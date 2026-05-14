import time
import os
from typing import Dict, Any
import tiktoken
import google.generativeai as genai
import logging

from app.models.schemas import InferenceRequest, PipelineMetrics, LLMInferenceResponse
from app.evaluation.concurrent import run_evaluations_concurrently

logger = logging.getLogger(__name__)

# Configure the Gemini client using the native SDK
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model_name = "gemini-3.1-flash-lite"
model = genai.GenerativeModel(model_name)

def count_tokens(text: str, model_name: str = "gemini-3.1-flash-lite") -> int:
    """Manually count tokens using tiktoken before dispatch as a rough estimation."""
    try:
        encoding = tiktoken.encoding_for_model("gpt-4") # Use a generic encoder for approximation
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

async def run_llm_only_inference(request: InferenceRequest) -> LLMInferenceResponse:
    """
    Executes raw inference without retrieval augmentation.
    """
    system_prompt = "You are a helpful assistant."
    user_query = request.query
    
    # Manual token counting
    prompt_tokens = count_tokens(system_prompt + " " + user_query)
    
    config = request.config
    temperature = config.temperature if config else 0.0
    max_tokens = config.max_tokens if config else 1024
    
    # Create generation config
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens
    )
    
    start_time = time.perf_counter()
    
    try:
        response = await model.generate_content_async(
            contents=[{"role": "user", "parts": [user_query]}],
            generation_config=generation_config
        )
        answer = response.text
        
    except Exception as e:
        logger.error(f"Error during LLM inference: {str(e)}")
        raise e
        
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000.0
    
    # Count completion tokens
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
        total_latency_ms=latency_ms,
        judge_score=judge_score,
        bert_score=bert_score
    )
    
    # We could log eval_latency_ms, but since it's not in the PipelineMetrics schema directly
    # (as total_latency is for the generation), we just log it for operational visibility.
    logger.info(f"LLM Only scientific grading phase took {eval_latency_ms:.2f} ms")

    return LLMInferenceResponse(answer=answer, metrics=metrics)
