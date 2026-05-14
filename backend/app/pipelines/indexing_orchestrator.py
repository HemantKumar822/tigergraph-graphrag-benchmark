import os
import re
import logging
import asyncio
import tiktoken
import json
from typing import Dict, Any, List
import uuid

# Try to import PyPDF2 or pypdf for PDF extraction
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False

from app.pipelines.basic_rag import collection
from app.pipelines.graphrag import tg_conn

logger = logging.getLogger(__name__)


META_FILE = os.path.join(os.getcwd(), "data", "ingestion_meta.json")

def get_total_tokens() -> int:
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r") as f:
                return json.load(f).get("total_tokens", 0)
        except:
            pass
    return 0

def add_tokens(count: int):
    current = get_total_tokens()
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump({"total_tokens": current + count}, f)

def reset_tokens():
    if os.path.exists(META_FILE):
        os.remove(META_FILE)

def count_tokens_exact(text: str) -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except:
        return int(len(text) / 4) # fallback approximation


def extract_text_from_pdf(file_path: str) -> str:
    if not PDF_SUPPORT:
        logger.warning("pypdf is not installed. PDF extraction will return empty string.")
        return ""
    
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"Failed to read PDF {file_path}: {e}")
        raise ValueError(f"Failed to parse PDF: {e}")
    return text

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read text file {file_path}: {e}")
            raise ValueError(f"Failed to parse text file: {e}")

def chunk_text(text: str, max_chunk_length: int = 1200) -> List[str]:
    # A simple paragraph-based or fixed-length chunker
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) <= max_chunk_length:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If a single paragraph is longer than max length, slice it
            if len(para) > max_chunk_length:
                for i in range(0, len(para), max_chunk_length):
                    chunks.append(para[i:i+max_chunk_length])
                current_chunk = ""
            else:
                current_chunk = para + "\n\n"
                
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks if chunks else [text[:max_chunk_length]]

def extract_entities(chunk: str) -> List[str]:
    """
    Build a robust set of entity candidates for graph linking.
    Includes capitalized phrases, acronyms, and high-signal lowercase technical terms.
    """
    # Capitalized multi-word phrases (e.g., "Artificial Intelligence", "TigerGraph Cloud")
    cap_phrases = re.findall(r'\b[A-Z][a-zA-Z0-9-]+(?:\s+[A-Z][a-zA-Z0-9-]+)*\b', chunk)

    # Acronyms / mixed alnum tokens (e.g., "AI", "LLM", "GPT-4", "AIOps")
    acronyms = re.findall(r'\b[A-Z]{2,}[A-Z0-9-]*\b', chunk)
    mixed_terms = re.findall(r'\b[a-zA-Z]+-[a-zA-Z0-9-]+\b', chunk)

    # Lowercase technical tokens improve recall for queries like "cloud computing".
    # Keep only strong candidates to avoid noisy graph explosion.
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "into", "their", "there", "have", "has",
        "had", "about", "which", "when", "where", "were", "been", "being", "would", "could", "should",
        "while", "within", "across", "also", "than", "then", "such", "using", "used", "use", "more",
        "most", "some", "many", "much", "very", "only", "over", "under", "between", "because", "through"
    }
    tokens = re.findall(r'\b[a-z][a-z0-9]{3,}\b', chunk.lower())
    freq: Dict[str, int] = {}
    for token in tokens:
        if token in stopwords:
            continue
        freq[token] = freq.get(token, 0) + 1

    # Keep top technical lowercase terms by frequency (cap to reduce edge blow-up)
    low_terms = [k for k, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30]]

    raw = cap_phrases + acronyms + mixed_terms + low_terms
    seen = set()
    entities: List[str] = []
    for term in raw:
        cleaned = term.strip()
        if len(cleaned) < 3:
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        entities.append(cleaned)

    return entities

async def stream_reindex_document(file_path: str):
    """
    Orchestrates chunking and injection, yielding real-time JSON log updates.
    Offloads synchronous blockers to thread executors to preserve async stream flushes.
    """
    import json
    fname = os.path.basename(file_path)
    
    logger.info(f"📂 [bold yellow]Triggering indexing workflow[/bold yellow] for file: [blue]{fname}[/blue]")
    yield f"data: {json.dumps({'event': 'status', 'msg': f'Initiating extraction for {fname}...', 'progress': 5})}\n\n"
    await asyncio.sleep(0.02) # Forces event loop scheduling and network flush
    
    try:
        # Run heavy PDF parse in background thread pool
        logger.info(f"🛠️ [cyan]Parsing file structure[/cyan]...")
        text = await asyncio.to_thread(extract_text, file_path)
        if not text.strip():
            logger.error("❌ Document text extraction yielded zero characters.")
            yield f"data: {json.dumps({'event': 'error', 'msg': 'Parsed document is empty. No text found.', 'progress': 100})}\n\n"
            return
    except Exception as e:
        logger.error(f"❌ Extraction abort: {e}", exc_info=True)
        yield f"data: {json.dumps({'event': 'error', 'msg': f'Extraction failed: {str(e)}', 'progress': 100})}\n\n"
        return

    
    exact_tokens = await asyncio.to_thread(count_tokens_exact, text)
    await asyncio.to_thread(add_tokens, exact_tokens)
    logger.info(f"✅ [green]Extracted {len(text)} characters ({exact_tokens} tokens)[/green] from document.")

    yield f"data: {json.dumps({'event': 'status', 'msg': 'Successfully extracted document text.', 'progress': 15})}\n\n"
    await asyncio.sleep(0.02)
    
    chunks = chunk_text(text)
    total_chunks = len(chunks)
    base_doc_id = str(uuid.uuid4())[:8]
    
    logger.info(f"📊 Document segmented into [cyan]{total_chunks}[/cyan] semantic chunks (Context Reference ID: [bold]{base_doc_id}[/bold]).")
    yield f"data: {json.dumps({'event': 'status', 'msg': f'Segmented document into {total_chunks} context chunks.', 'progress': 20})}\n\n"
    await asyncio.sleep(0.02)

    # --- Vector Injection ---
    vector_ids = []
    if collection:
        try:
            logger.info("⚡ [magenta]Commencing ChromaDB Vector injection[/magenta]...")
            yield f"data: {json.dumps({'event': 'status', 'msg': f'Commencing Vector DB (Chroma) injection...', 'progress': 25})}\n\n"
            await asyncio.sleep(0.02)
            vector_ids = [f"doc_{base_doc_id}_{i}" for i in range(len(chunks))]
            batch_size = 50 # smaller batches for smoother updates
            
            for i in range(0, len(chunks), batch_size):
                end_idx = min(i + batch_size, len(chunks))
                # Run blocking network call in thread
                await asyncio.to_thread(
                    collection.add,
                    documents=chunks[i:end_idx],
                    ids=vector_ids[i:end_idx]
                )
                prog = 25 + int((end_idx / total_chunks) * 25) # maps to 25%-50% range
                msg = f"⚡ Vectorized {end_idx}/{total_chunks} chunks ({prog}% Complete)"
                logger.info(f"    ↳ {msg}")
                yield f"data: {json.dumps({'event': 'status', 'msg': msg, 'progress': prog})}\n\n"
                await asyncio.sleep(0.05) # Yield control back to flush response
            
            logger.info("✅ [green]Vector injection complete[/green]. Database synchronized.")
            yield f"data: {json.dumps({'event': 'status', 'msg': '✅ Vector knowledge store populated.', 'progress': 50})}\n\n"
            await asyncio.sleep(0.02)
        except Exception as e:
            logger.error(f"⚠️ Vector injection failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'warning', 'msg': f'Vector store failed: {str(e)}'})}\n\n"
    else:
        logger.warning("⚠️ Vector DB collection not found. Skipping phase.")
        yield f"data: {json.dumps({'event': 'warning', 'msg': 'Vector collection missing. Skipping step.', 'progress': 50})}\n\n"

    # --- Graph Injection ---
    entities_upserted = 0
    if tg_conn:
        logger.info("🕸️ [magenta]Commencing TigerGraph Cloud vertex construction[/magenta]...")
        yield f"data: {json.dumps({'event': 'status', 'msg': f'Commencing TigerGraph vertex construction...', 'progress': 55})}\n\n"
        await asyncio.sleep(0.02)
        try:
            doc_batch = []
            ent_batch_dict = {}  # Deduplicate entities within the active batch window
            edge_batch = []
            
            BATCH_WINDOW = 10  # Flush accumulated graph data every 10 chunks
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"doc_{base_doc_id}_{i}"
                
                # Stage local data structure mutations in memory
                doc_batch.append((chunk_id, {"content": chunk}))
                
                extracted = extract_entities(chunk)
                for ent in extracted:
                    ent_batch_dict[ent] = {"name": ent}
                    edge_batch.append((chunk_id, ent, {}))
                    entities_upserted += 1
                
                # Trigger vectorized transactional write when window closes or EOF reached
                if (i + 1) % BATCH_WINDOW == 0 or i == total_chunks - 1:
                    # 1. Bulk Upsert staged Document vertices
                    if doc_batch:
                        await asyncio.to_thread(tg_conn.upsertVertices, "Document", doc_batch)
                    
                    # 2. Bulk Upsert stage-deduplicated Entity vertices
                    if ent_batch_dict:
                        ent_tuple_list = list(ent_batch_dict.items())
                        await asyncio.to_thread(tg_conn.upsertVertices, "Entity", ent_tuple_list)
                        
                    # 3. Bulk Upsert all staged relationship Edges
                    if edge_batch:
                        await asyncio.to_thread(tg_conn.upsertEdges, "Document", "HAS_ENTITY", "Entity", edge_batch)
                    
                    # Flush local staging memory buffers
                    doc_batch = []
                    ent_batch_dict = {}
                    edge_batch = []
                    
                    # Emit streaming visual telemetry telemetry
                    prog = 55 + int(((i + 1) / total_chunks) * 40) # maps to 55%-95% range
                    msg = f"🔗 Graph linking: Progressing {i+1}/{total_chunks} chunks ({entities_upserted} total edges)"
                    logger.info(f"    ↳ {msg}")
                    yield f"data: {json.dumps({'event': 'status', 'msg': msg, 'progress': prog})}\n\n"
                    await asyncio.sleep(0.05)  # Yield to async loop to ensure network frame flush

            
            logger.info(f"✅ [green]TigerGraph linking complete[/green]. Formed [bold]{entities_upserted}[/bold] distinct entity edges.")
            yield f"data: {json.dumps({'event': 'status', 'msg': f'✅ Graph ingestion complete. Created {entities_upserted} relationships.', 'progress': 95})}\n\n"
            await asyncio.sleep(0.02)
        except Exception as e:
            import requests
            error_msg = str(e)
            is_sleeping = False
            
            # Unpack and inspect the server response body to detect TigerGraph Cloud Hibernation
            if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                try:
                    content = e.response.text or ""
                    if "Failed to start workspace" in content or "Auto start is not enabled" in content:
                        is_sleeping = True
                except Exception:
                    pass
            
            # Fallback text matching
            if not is_sleeping and ("Failed to start workspace" in error_msg or "Auto start is not" in error_msg):
                is_sleeping = True
                
            if is_sleeping:
                actionable_warning = "💤 TIGERGRAPH SLEEPING: Your Cloud Free-Tier workspace has hibernated. Log in to https://tgcloud.io and click 'START' to wake it up!"
                logger.critical(f"🚨 [bold red]{actionable_warning}[/bold red]")
                yield f"data: {json.dumps({'event': 'warning', 'msg': actionable_warning, 'progress': 95})}\n\n"
            else:
                logger.error(f"⚠️ TigerGraph Ingestion crash: {e}", exc_info=True)
                yield f"data: {json.dumps({'event': 'warning', 'msg': f'Graph engine failed: {str(e)}'})}\n\n"
    else:
         logger.warning("⚠️ TigerGraph Offline. Skipping phase.")
         yield f"data: {json.dumps({'event': 'warning', 'msg': 'TigerGraph connection offline. Skipping step.', 'progress': 95})}\n\n"

    # --- Summary ---
    final_vector = await asyncio.to_thread(collection.count) if collection else 0
    logger.info(f"🎉 [bold green]System optimization routine complete![/bold green] Indexed {total_chunks} chunks and built {entities_upserted} nodes.")
    yield f"data: {json.dumps({'event': 'complete', 'msg': 'System fully optimized & indexed!', 'summary': {'chunks': total_chunks, 'vectors': final_vector, 'entities': entities_upserted}, 'progress': 100})}\n\n"

async def reindex_document(file_path: str) -> Dict[str, Any]:
    """
    Convenience wrapper for tests and scripts that need a final summary instead
    of consuming the SSE stream manually.
    """
    summary = {
        "status": "error",
        "chunks": 0,
        "vector_count": 0,
        "entities": 0,
    }

    async for frame in stream_reindex_document(file_path):
        if not frame.startswith("data: "):
            continue

        payload = frame[6:].strip()
        if not payload:
            continue

        import json

        data = json.loads(payload)
        if data.get("event") == "complete":
            stats = data.get("summary", {})
            summary.update(
                {
                    "status": "success",
                    "chunks": stats.get("chunks", 0),
                    "vector_count": stats.get("vectors", 0),
                    "entities": stats.get("entities", 0),
                }
            )
        elif data.get("event") == "error":
            summary["message"] = data.get("msg", "Indexing failed")

    return summary

async def clear_all_databases() -> Dict[str, Any]:
    """
    Safely clears the Vector DB collection and deletes specific GraphRAG entities to start fresh.
    """
    logger.info("Initiating system-wide data clearance sequence...")
    results = {
        "vector_db": "skipped",
        "graph_db": "skipped",
        "tokens": "skipped"
    }
    
    # 1. Clear ChromaDB (Vector)
    if collection:
        try:
            current_ids = collection.get()["ids"]
            if current_ids:
                collection.delete(ids=current_ids)
                results["vector_db"] = f"success (purged {len(current_ids)} IDs)"
            else:
                results["vector_db"] = "success (already empty)"
        except Exception as e:
            logger.error(f"Failed to clear Vector DB: {e}")
            results["vector_db"] = f"error: {str(e)}"
            
    # 2. Clear Graph DB (Specific vertices only)
    if tg_conn:
        try:
            # Using deleteVertices with blank where implies all
            del_doc = tg_conn.delVertices("Document")
            del_ent = tg_conn.delVertices("Entity")
            results["graph_db"] = "success (Documents & Entities purged)"
        except Exception as e:
            # Fallback to GSQL if REST deletion fails
            try:
                graph_name = tg_conn.graphname
                gsql_cmd = f"USE GRAPH {graph_name}\nDELETE a FROM Document:a;\nDELETE b FROM Entity:b;\n"
                tg_conn.gsql(gsql_cmd)
                results["graph_db"] = "success (purged via GSQL fallback)"
            except Exception as e2:
                logger.error(f"Failed to clear Graph DB: {e2}")
                results["graph_db"] = f"error: {str(e2)}"
    
    # 3. Reset token count
    try:
        reset_tokens()
        results["tokens"] = "success (token count reset to 0)"
    except Exception as e:
        logger.error(f"Failed to reset token count: {e}")
        results["tokens"] = f"error: {str(e)}"
                
    logger.info(f"Data clearance complete: {results}")
    return results
