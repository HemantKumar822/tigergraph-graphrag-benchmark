import time
import random
import os
import logging
from typing import List
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from app.models.schemas import InferenceRequest, LLMInferenceResponse, PipelineMetrics
from app.evaluation.concurrent import run_evaluations_concurrently
from app.core.config import settings
import tiktoken

logger = logging.getLogger(__name__)

# Configure the Gemini client using the native SDK
genai.configure(api_key=settings.GEMINI_API_KEY)
model_name = "gemini-3.1-flash-lite"
model = genai.GenerativeModel(model_name)

# Initialize ChromaDB. Tests stay ephemeral; local/dev runs can persist.
chroma_client = chromadb.Client(
    Settings(
        is_persistent=not settings.TESTING,
        persist_directory=settings.CHROMA_PERSIST_PATH,
    )
)

from chromadb import Documents, EmbeddingFunction, Embeddings

class CustomGeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="models/text-embedding-004"):
        self.model_name = model_name
        
    def __call__(self, input: Documents) -> Embeddings:
        max_attempts = 6
        initial_delay = 2.5
        
        for attempt in range(max_attempts):
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=input
                )
                if 'embedding' not in result:
                    raise ValueError(f"Corrupted Gemini API Response: Got keys: {list(result.keys())}")
                return result['embedding']
            except Exception as e:
                err_str = str(e)
                is_429 = "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str or "limit" in err_str.lower()
                
                if is_429 and attempt < max_attempts - 1:
                    import random
                    sleep_sec = (initial_delay * (2 ** attempt)) + (random.uniform(0.5, 2.0))
                    logger.warning(f"⚠️ [Gemini Rate Limit (429)] Quota saturated. Retrying in {sleep_sec:.2f}s (Attempt {attempt + 1}/{max_attempts})...")
                    import time
                    time.sleep(sleep_sec)
                    continue
                
                logger.error(f"❌ Resiliency Layer Exhausted or API Fault: {err_str}")
                raise e

# Initialize 100% Local Embedding Function (Zero API, Zero latency, Zero 429s)
from chromadb.utils import embedding_functions
local_ef = embedding_functions.DefaultEmbeddingFunction()

# Create a collection
COLLECTION_NAME = "sample_documents_local"
try:
    # Attempt loading with local high-speed embeddings
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, 
        embedding_function=local_ef
    )
    logger.info(f"✅ Collection '{COLLECTION_NAME}' loaded with local ONNX embeddings.")
except Exception as e:
    logger.warning(f"Dimensionality/Embedding mismatch in collection (common when switching models). Automatically recreating... Detail: {e}")
    try:
        # Natively purge the legacy collection to clear dimensionality conflicts
        chroma_client.delete_collection(COLLECTION_NAME)
        collection = chroma_client.create_collection(
            name=COLLECTION_NAME, 
            embedding_function=local_ef
        )
        logger.info(f"🎉 Successfully purged and recreated collection '{COLLECTION_NAME}' with local embeddings.")
    except Exception as recreate_err:
        logger.error(f"CRITICAL: Failed to recreate collection with local embeddings: {recreate_err}")
        collection = None

# Prime the collection with some sample documents
sample_docs = [
    "TigerGraph is a native distributed graph database.",
    "GraphRAG combines knowledge graphs with large language models to improve context retrieval.",
    "ChromaDB is an open-source vector database designed for AI applications.",
    "Semantic search uses embeddings to find documents with similar meanings rather than exact keyword matches."
]
if collection and collection.count() == 0 and os.environ.get("TESTING") != "true":
    try:
        collection.add(
            documents=sample_docs,
            ids=[f"doc_{i}" for i in range(len(sample_docs))]
        )
    except Exception as e:
        logger.error(f"Failed to prime ChromaDB collection: {e}")

def count_tokens(text: str, model_name: str = "gemini-3.1-flash-lite") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text))

async def run_basic_rag_inference(request: InferenceRequest) -> LLMInferenceResponse:
    if not collection:
        raise RuntimeError("ChromaDB collection is not initialized.")
    
    total_start_time = time.perf_counter()
    
    # 1. Semantic Search (Retrieval)
    search_start = time.perf_counter()
    results = collection.query(
        query_texts=[request.query],
        n_results=request.config.top_k if request.config and request.config.top_k else settings.DEFAULT_TOP_K
    )
    search_end = time.perf_counter()
    semantic_search_latency_ms = (search_end - search_start) * 1000

    # 2. Context Aggregation
    retrieved_docs = results['documents'][0] if results['documents'] else []
    context_block = "\n".join(retrieved_docs)
    
    system_prompt = (
        "You are a knowledgeable and highly capable AI assistant.\n"
        "You have access to retrieved context, but you must answer seamlessly.\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. Do NOT use phrases like 'Based on the context', 'According to the text', or 'I don't have the context'.\n"
        "2. Answer the user's question directly, factually, and confidently.\n"
        "3. If the context makes it possible, just answer it. Answer seamlessly without disclaimers.\n\n"
        "Context:\n"
        f"{context_block}"
    )
    
    # 3. LLM Generation
    prompt_tokens = count_tokens(system_prompt) + count_tokens(request.query)
    
    temperature = request.config.temperature if request.config else 0.0
    max_tokens = request.config.max_tokens if request.config else 1024

    # Create generation config
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens
    )

    response = await model.generate_content_async(
        contents=[
            {"role": "user", "parts": [system_prompt]},
            {"role": "user", "parts": [request.query]}
        ],
        generation_config=generation_config
    )
    
    total_end_time = time.perf_counter()
    total_latency_ms = (total_end_time - total_start_time) * 1000
    
    answer = response.text
    completion_tokens = count_tokens(answer)
    
    # Concurrent Evaluation Phase
    eval_start_time = time.perf_counter()
    judge_score = None
    bert_score = None
    if request.ground_truth:
        judge_score, bert_score = await run_evaluations_concurrently(
            ground_truth=request.ground_truth,
            answer=answer
        )
    eval_end_time = time.perf_counter()
    eval_latency_ms = (eval_end_time - eval_start_time) * 1000.0

    metrics = PipelineMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        semantic_search_latency_ms=round(semantic_search_latency_ms, 2),
        total_latency_ms=round(total_latency_ms, 2),
        judge_score=judge_score,
        bert_score=bert_score
    )
    
    logger.info(f"Basic RAG scientific grading phase took {eval_latency_ms:.2f} ms")

    return LLMInferenceResponse(
        answer=answer,
        metrics=metrics
    )
