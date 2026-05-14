import logging
import re
import time
from typing import Any

import httpx
import pyTigerGraph as tg
import tiktoken

from app.core.config import settings
from app.evaluation.concurrent import run_evaluations_concurrently
from app.models.schemas import InferenceRequest, LLMInferenceResponse, PipelineMetrics

logger = logging.getLogger(__name__)


def count_tokens(text: str, model_name: str = "gemini-3.1-flash-lite") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text))


def _get_jwt_token_from_secret(host: str, secret: str) -> str | None:
    """Fallback for modern TigerGraph Cloud V4 clusters that require /gsql/v1/tokens."""
    url = f"{host}/gsql/v1/tokens"
    try:
        # Ensure no proxy interference on local loop
        res = httpx.post(url, json={"secret": secret}, verify=False, timeout=10.0, trust_env=False)
        if res.status_code == 200:
            data = res.json()
            if not data.get("error") and "token" in data:
                return str(data["token"])
    except Exception as e:
        logger.warning("Failed modern JWT gateway fetch: %s", e)
    return None


def _build_tg_connection() -> tg.TigerGraphConnection | None:
    if not settings.has_real_tg_host() or not settings.TG_GRAPH:
        return None
    if not settings.has_direct_tg_credentials():
        return None

    common_kwargs: dict[str, Any] = {
        "host": settings.TG_HOSTNAME,
        "graphname": settings.TG_GRAPH,
    }

    if settings.TG_AUTH_MODE == "token":
        common_kwargs.update(
            {
                "apiToken": settings.TG_API_TOKEN,
                "tgCloud": settings.TG_USE_CLOUD,
                "sslPort": settings.TG_SSL_PORT,
            }
        )
        if settings.TG_USERNAME:
            common_kwargs["username"] = settings.TG_USERNAME
        if settings.TG_PASSWORD:
            common_kwargs["password"] = settings.TG_PASSWORD
    elif settings.TG_AUTH_MODE == "secret":
        # Bypassing fragile SDK token fetching: explicitly generate our own token!
        jwt_token = _get_jwt_token_from_secret(settings.TG_HOSTNAME, settings.TG_SECRET)
        if jwt_token:
            logger.info("Using manually generated dynamic JWT for connection.")
            common_kwargs.update(
                {
                    "apiToken": jwt_token,
                    "tgCloud": settings.TG_USE_CLOUD,
                    "sslPort": settings.TG_SSL_PORT,
                }
            )
        else:
            logger.warning("Falling back to standard secret mode.")
            common_kwargs.update(
                {
                    "gsqlSecret": settings.TG_SECRET,
                    "tgCloud": settings.TG_USE_CLOUD,
                    "sslPort": settings.TG_SSL_PORT,
                }
            )
        if settings.TG_USERNAME:
            common_kwargs["username"] = settings.TG_USERNAME
    else:
        common_kwargs.update(
            {
                "username": settings.TG_USERNAME,
                "password": settings.TG_PASSWORD,
                "restppPort": settings.TG_RESTPP_PORT,
                "gsPort": settings.TG_GSQL_PORT,
            }
        )

    conn = tg.TigerGraphConnection(**common_kwargs)
    
    # Resiliency Hook: Force SDK to fetch RESTPP active token if not already set and secret is available
    if not getattr(conn, "apiToken", None) and settings.TG_SECRET:
        try:
            logger.info("Requesting dynamic RESTPP access token via pyTigerGraph SDK...")
            conn.getToken(settings.TG_SECRET)
            conn._refresh_auth_headers()
            logger.info("Successfully acquired active dynamic access token.")
        except Exception as token_err:
            import requests
            is_sleeping = False
            if isinstance(token_err, requests.exceptions.HTTPError) and token_err.response is not None:
                try:
                    content = token_err.response.text or ""
                    if "Failed to start workspace" in content or "Auto start is not enabled" in content:
                        is_sleeping = True
                except Exception:
                    pass
            if not is_sleeping and ("Failed to start workspace" in str(token_err) or "500 Server Error" in str(token_err)):
                is_sleeping = True
                
            if is_sleeping:
                logger.critical("🚨 [bold red]TIGERGRAPH IS ASLEEP[/bold red]: Your TigerGraph Cloud Free-Tier workspace has hibernated. Log in to https://tgcloud.io and click 'START' to wake it up!")
            else:
                logger.error(f"Failed to fetch token via pyTigerGraph SDK: {token_err}")

    try:
        conn.customizeHeader(timeout=60_000, responseSize=5_000_000)
    except Exception:
        logger.debug("TigerGraph header customization skipped.", exc_info=True)
    return conn


tg_conn = None
try:
    tg_conn = _build_tg_connection()
    if tg_conn:
        logger.info("TigerGraph connection initialized for %s", settings.TG_HOSTNAME)
except Exception as conn_err:
    logger.error("Failed to establish TigerGraph connection: %s", conn_err)
    tg_conn = None


def _safe_fetch_document(document_id: str) -> str:
    if not tg_conn:
        return ""

    try:
        result = tg_conn.getVerticesById("Document", document_id)
        if isinstance(result, list) and result:
            return result[0].get("attributes", {}).get("content", "")
        if isinstance(result, dict):
            return result.get("attributes", {}).get("content", "")
    except Exception as e:
        logger.debug("Failed to fetch document %s: %s", document_id, e)
    return ""


def _keyword_candidates(query: str) -> list[str]:
    from app.pipelines.indexing_orchestrator import extract_entities
    import re

    # 1. Start with strictly matched multi-word entities
    candidates = set(extract_entities(query))

    # 2. Smart Query Expansion: Extract and normalize tokens to align case-sensitive graph
    clean_query = re.sub(r"['’]s\b", "", query)  # strip possessives (e.g. NVIDIA's -> NVIDIA)
    words = re.findall(r"\b\w+\b", clean_query)

    # Standard query stop-words to ignore
    stopwords = {
        "what", "was", "were", "for", "the", "and", "are", "that", "with",
        "from", "this", "these", "those", "have", "has", "had", "does", "did",
        "your", "their", "them", "then", "than", "about", "much", "many", "more"
    }

    for word in words:
        word_clean = word.strip()
        if len(word_clean) < 3 or word_clean.lower() in stopwords:
            continue
        
        # Add original word
        candidates.add(word_clean)
        # Inject casing variants since TigerGraph entity vertex-ids are case-sensitive!
        candidates.add(word_clean.lower())
        candidates.add(word_clean.capitalize())
        candidates.add(word_clean.upper())

    return list(candidates)


def _neighbors_for_entity(entity_id: str) -> list[dict[str, Any]]:
    if not tg_conn:
        return []
    try:
        # Using correct, officially supported getEdges endpoint for the undirected HAS_ENTITY relation
        return tg_conn.getEdges("Entity", entity_id, edgeType="HAS_ENTITY") or []
    except Exception as e:
        logger.debug("Failed to fetch edges for entity %s: %s", entity_id, e)
        return []


def _retrieve_graph_context(query: str, top_k: int, num_hops: int) -> list[str]:
    if not tg_conn:
        if settings.TESTING:
            return [
                "TigerGraph test context: GraphRAG retrieves evidence through entity-document links and multi-hop graph reasoning."
            ]
        raise RuntimeError(
            "TigerGraph connection is not established. Verify Savanna endpoint and credentials."
        )

    entity_frontier = set(_keyword_candidates(query))
    if not entity_frontier:
        return []

    doc_rankings: dict[str, float] = {}
    collected_docs: set[str] = set()

    # --- Step 1: Direct Traversal (Entity -> Document) ---
    import concurrent.futures

    def fetch_ent_edges(ent):
        try:
            return tg_conn.getEdges("Entity", ent, edgeType="HAS_ENTITY") or []
        except:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for edges in executor.map(fetch_ent_edges, entity_frontier):
            for edge in edges:
                # Extract target document ID
                doc_id = edge.get("to_id") or edge.get("v_id") or edge.get("vId")
                if doc_id:
                    # Directly matching entities give a strong base signal
                    doc_rankings[doc_id] = doc_rankings.get(doc_id, 0.0) + 10.0
                    collected_docs.add(doc_id)

    # --- Step 2: Semantic Multi-Hop Expansion (Document -> Entity -> Document) ---
    # Optimization: Only perform semantic hops if we have matches, and limit to top 10 docs
    # to prevent N+1 query amplification latency.
    if num_hops > 1 and collected_docs:
        top_direct_docs = [
            doc_id for doc_id, _ in sorted(doc_rankings.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        expanded_entities: set[str] = set()
        # Hop 2.1: From Top Documents, extract other associated Entities
        def fetch_doc_entity_edges(doc_id):
            try: return tg_conn.getEdges("Document", doc_id, edgeType="HAS_ENTITY") or []
            except: return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for edges in executor.map(fetch_doc_entity_edges, top_direct_docs):
                for edge in edges:
                    ent_id = edge.get("to_id") or edge.get("v_id") or edge.get("vId")
                    if ent_id and ent_id not in entity_frontier:
                        expanded_entities.add(ent_id)
        
        import concurrent.futures

        # Hop 2.2: From Expanded Entities, find additional related Documents
        # Limit to 30 most relevant expanding entities to avoid 100+ second latency
        limited_entities = list(expanded_entities)[:30]
        
        def fetch_doc_edges(ent):
            try:
                return tg_conn.getEdges("Entity", ent, edgeType="HAS_ENTITY") or []
            except:
                return []
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for edges in executor.map(fetch_doc_edges, limited_entities):
                for edge in edges:
                    d_id = edge.get("to_id") or edge.get("v_id") or edge.get("vId")
                    if d_id:
                        # Indirect matches contribute slightly to boost related/adjacent context,
                        # but must not overwhelm direct direct semantic hits.
                        doc_rankings[d_id] = doc_rankings.get(d_id, 0.0) + 0.1

    # Sort by descending rank with ID tie-breaker
    # Fetch a slightly larger candidate pool, then rerank by lexical overlap.
    prefetch_k = min(max(top_k * 3, top_k), 30)
    sorted_docs = sorted(
        doc_rankings.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )[:prefetch_k]
    
    top_doc_ids = [doc_id for doc_id, _ in sorted_docs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=top_k) as executor:
        contents = list(executor.map(_safe_fetch_document, top_doc_ids))
        
    query_terms = {
        token.lower()
        for token in re.findall(r"\b[a-zA-Z0-9]{2,}\b", query)
        if token.lower() not in {
            "what", "which", "when", "where", "why", "how", "the", "and", "for", "with",
            "from", "this", "that", "into", "about", "does", "have", "has", "had"
        }
    }

    def overlap_score(text: str) -> int:
        low = text.lower()
        return sum(1 for t in query_terms if t in low)

    def focused_snippet(text: str, max_chars: int = 700) -> str:
        if not text:
            return ""
        if not query_terms:
            return text[:max_chars]

        low = text.lower()
        window = 900
        step = 300
        best_start = 0
        best_hits = -1

        for start in range(0, max(1, len(text) - window + 1), step):
            seg = low[start : start + window]
            hits = sum(1 for t in query_terms if t in seg)
            if hits > best_hits:
                best_hits = hits
                best_start = start

        if best_hits <= 0:
            return text[:max_chars]

        start = max(0, best_start - 150)
        end = min(len(text), start + max_chars)
        return text[start:end]

    scored: list[tuple[float, int, str]] = []
    for doc_id, raw in zip(top_doc_ids, contents):
        if not raw:
            continue
        base_rank = doc_rankings.get(doc_id, 0.0)
        lexical = overlap_score(raw)
        scored.append((base_rank + (lexical * 2.0), lexical, focused_snippet(raw)))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Keep prompt compact: select only the most query-aligned snippets up to a character budget.
    selected: list[str] = []
    char_budget = 2600
    total_chars = 0
    for _, lexical, snippet in scored:
        if not snippet:
            continue
        # Allow low-overlap snippets only if we still have little evidence.
        if lexical == 0 and len(selected) >= 2:
            continue
        if total_chars + len(snippet) > char_budget and selected:
            continue
        selected.append(snippet)
        total_chars += len(snippet)
        if len(selected) >= top_k:
            break

    return selected


def _service_request_parts() -> tuple[dict[str, str], tuple[str, str] | None]:
    headers: dict[str, str] = {}
    auth = None

    if settings.GRAPHRAG_SERVICE_AUTH_MODE == "bearer":
        if settings.GRAPHRAG_SERVICE_API_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GRAPHRAG_SERVICE_API_TOKEN}"
    elif settings.GRAPHRAG_SERVICE_AUTH_MODE == "basic":
        auth = (
            settings.GRAPHRAG_SERVICE_USERNAME,
            settings.GRAPHRAG_SERVICE_PASSWORD,
        )

    return headers, auth


async def _query_official_graphrag_service(
    request: InferenceRequest,
) -> tuple[str, float]:
    if not settings.GRAPHRAG_SERVICE_ENABLED:
        raise RuntimeError("Official GraphRAG service integration is disabled.")
    if not settings.has_graphrag_service_auth():
        raise RuntimeError("Official GraphRAG service authentication is not configured.")

    url = (
        f"{settings.GRAPHRAG_SERVICE_URL.rstrip('/')}"
        f"/{settings.GRAPHRAG_SERVICE_GRAPH}/query"
    )
    payload: dict[str, Any] = {"query": request.query}
    if settings.GRAPHRAG_SERVICE_RAG_METHOD:
        payload["rag_method"] = settings.GRAPHRAG_SERVICE_RAG_METHOD

    headers, auth = _service_request_parts()
    service_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=settings.GRAPHRAG_SERVICE_TIMEOUT_S) as client:
        response = await client.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        body = response.json()
    service_latency_ms = (time.perf_counter() - service_start) * 1000.0

    answer = body.get("natural_language_response")
    if not answer:
        raise RuntimeError("Official GraphRAG service returned an empty answer.")

    return answer, service_latency_ms


async def run_graphrag_inference(request: InferenceRequest) -> LLMInferenceResponse:
    total_start_time = time.perf_counter()
    top_k = request.config.top_k if request.config and request.config.top_k else settings.DEFAULT_TOP_K
    num_hops = (
        request.config.num_hops
        if request.config and request.config.num_hops
        else settings.DEFAULT_NUM_HOPS
    )

    answer: str | None = None
    graph_traversal_latency_ms: float | None = None
    prompt_tokens = count_tokens(request.query)

    if settings.GRAPHRAG_SERVICE_ENABLED:
        try:
            answer, graph_traversal_latency_ms = await _query_official_graphrag_service(request)
        except Exception as exc:
            if not settings.GRAPHRAG_DIRECT_FALLBACK:
                raise RuntimeError(
                    f"Official GraphRAG service call failed: {exc}"
                ) from exc
            logger.warning(
                "Official GraphRAG service failed, falling back to direct retrieval: %s",
                exc,
            )

    if answer is None:
        search_start = time.perf_counter()
        graph_context = _retrieve_graph_context(request.query, top_k, num_hops)

        # Hybrid rescue: merge a small semantic slice with graph evidence and rerank.
        vector_context: list[str] = []
        try:
            from app.pipelines.basic_rag import collection as vector_collection

            if vector_collection:
                vector_hits = vector_collection.query(
                    query_texts=[request.query],
                    n_results=max(3, min(max(top_k * 2, top_k), 10)),
                )
                vector_context = vector_hits.get("documents", [[]])[0] or []
        except Exception as fallback_err:
            logger.debug("Vector assist for GraphRAG skipped: %s", fallback_err)

        query_terms = {
            token.lower()
            for token in re.findall(r"\b[a-zA-Z0-9]{2,}\b", request.query)
            if token.lower() not in {
                "what", "which", "when", "where", "why", "how", "the", "and", "for", "with",
                "from", "this", "that", "into", "about", "does", "have", "has", "had"
            }
        }

        combined: list[tuple[str, str]] = []
        for txt in graph_context:
            combined.append(("graph", txt))
        for txt in vector_context:
            combined.append(("vector", txt))

        deduped: list[tuple[str, str]] = []
        seen_keys: set[str] = set()
        for src, txt in combined:
            key = re.sub(r"\s+", " ", txt.strip().lower())[:220]
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append((src, txt[:700]))

        ranked: list[tuple[float, str]] = []
        for src, txt in deduped:
            low = txt.lower()
            overlap = sum(1 for t in query_terms if t in low)
            ranked.append((float(overlap), txt))

        ranked.sort(key=lambda x: x[0], reverse=True)

        # Seed with strongest semantic hits for recall, then enrich with graph-ranked snippets.
        final_context: list[str] = []
        seen_seed: set[str] = set()
        top_limit = max(1, top_k)
        for txt in vector_context[:top_limit]:
            clean = (txt or "")[:700]
            key = re.sub(r"\s+", " ", clean.strip().lower())[:220]
            if not clean or key in seen_seed:
                continue
            seen_seed.add(key)
            final_context.append(clean)

        for _, txt in ranked:
            key = re.sub(r"\s+", " ", txt.strip().lower())[:220]
            if not txt or key in seen_seed:
                continue
            final_context.append(txt)
            seen_seed.add(key)
            if len(final_context) >= top_limit:
                break

        if not final_context:
            logger.info("GraphRAG had no usable context after hybrid merge.")

        retrieved_context = (
            "\n---\n".join(final_context)
            or "No graph entities matched the user query in the knowledge database."
        )
        graph_traversal_latency_ms = (time.perf_counter() - search_start) * 1000.0

        final_prompt = (
            "You are a knowledgeable and highly capable AI assistant answering a query based on a graph database.\n"
            "Produce a direct, concrete answer first, then include concise evidence bullets from context.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Do NOT use phrases like 'Based on the context', 'According to the text', or 'I don't have the context'.\n"
            "2. Answer the user's question directly, factually, and confidently.\n"
            "3. If context is partial, answer using your best judgment. Answer seamlessly without disclaimers.\n\n"
            f"CONTEXT:\n{retrieved_context}\n\n"
            f"QUERY:\n{request.query}\n\n"
            "Output format:\n"
            "Direct Answer: <2-6 sentences>\n"
            "Evidence:\n"
            "- <bullet 1>\n"
            "- <bullet 2>\n"
        )

        from app.pipelines.llm_only import model as llm_model

        try:
            response = await llm_model.generate_content_async(
                contents=[{"role": "user", "parts": [final_prompt]}]
            )
            answer = response.text
            prompt_tokens = count_tokens(final_prompt)
        except Exception as exc:
            logger.error("GraphRAG answer synthesis failed: %s", exc)
            raise RuntimeError(f"GraphRAG pipeline failed: {str(exc)}") from exc

    completion_tokens = count_tokens(answer)
    total_latency_ms = (time.perf_counter() - total_start_time) * 1000.0

    judge_score = None
    bert_score = None
    if request.ground_truth:
        judge_score, bert_score = await run_evaluations_concurrently(
            ground_truth=request.ground_truth,
            answer=answer,
        )

    metrics = PipelineMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        graph_traversal_latency_ms=round(graph_traversal_latency_ms or 0.0, 2),
        total_latency_ms=round(total_latency_ms, 2),
        judge_score=judge_score,
        bert_score=bert_score,
    )

    return LLMInferenceResponse(answer=answer, metrics=metrics)
