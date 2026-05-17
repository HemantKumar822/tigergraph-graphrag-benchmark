"""
Benchmark orchestrator: fires all three inference pipelines concurrently via
asyncio.gather(return_exceptions=True) and returns a composite result.

Fault isolation: if any individual pipeline raises, its slot in the response
is populated with a PipelineResult(status="error", error=<message>) so the
other two pipelines can still return their data.
"""
import asyncio
import logging
from fastapi import APIRouter
from app.models.schemas import (
    InferenceRequest,
    APIResponse,
    APIError,
    PipelineResult,
    BenchmarkResults,
    BenchmarkResponse,
)
from app.pipelines.llm_only import run_llm_only_inference
from app.pipelines.basic_rag import run_basic_rag_inference
from app.pipelines.graphrag import run_graphrag_inference
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

orchestrator = APIRouter(prefix="/api/orchestrator")


def _pipeline_result(outcome) -> PipelineResult:
    """
    Convert an asyncio.gather result slot to a PipelineResult.
    The slot is either a successful LLMInferenceResponse or a BaseException
    (because gather is called with return_exceptions=True). We check against
    BaseException (not just Exception) to correctly handle KeyboardInterrupt,
    GeneratorExit, and other non-Exception BaseException subclasses.
    """
    if isinstance(outcome, BaseException):
        logger.error(f"Pipeline failed: {outcome}")
        return PipelineResult(status="error", error=str(outcome))
    return PipelineResult(status="success", data=outcome)


@orchestrator.post("/benchmark", response_model=APIResponse[BenchmarkResponse])
async def benchmark_endpoint(request: InferenceRequest):
    """
    Concurrently executes all three pipelines (llm-only, basic-rag, graphrag)
    using asyncio.gather with return_exceptions=True so that a single pipeline
    failure does not abort the others. Auto-generates ground truth if missing.
    """
    try:
        # Auto-generate Ground Truth if missing to make evaluation seamless and automatic
        if not request.ground_truth or not request.ground_truth.strip():
            auto_model = genai.GenerativeModel("gemini-3.1-flash-lite")
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
            try:
                gen_resp = await auto_model.generate_content_async(
                    f"Provide a concise, factual, and accurate answer to this question: {request.query}. "
                    "Make it exactly 1-2 sentences. No conversational filler."
                )
                request.ground_truth = gen_resp.text.strip()
                logger.info(f"Auto-generated ground truth: {request.ground_truth}")
            except Exception as e:
                logger.warning(f"Failed to auto-generate ground truth: {e}")

        llm_task = run_llm_only_inference(request)
        rag_task = run_basic_rag_inference(request)
        graph_task = run_graphrag_inference(request)

        llm_result, rag_result, graph_result = await asyncio.gather(
            llm_task, rag_task, graph_task,
            return_exceptions=True
        )

        benchmark_results = BenchmarkResults(
            llm_only=_pipeline_result(llm_result),
            basic_rag=_pipeline_result(rag_result),
            graph_rag=_pipeline_result(graph_result),
        )

        return APIResponse(
            status="success",
            data=BenchmarkResponse(results=benchmark_results)
        )
    except Exception as e:
        logger.error(f"Orchestrator failed unexpectedly: {e}")
        return APIResponse(
            status="error",
            error=APIError(code="ORCHESTRATOR_ERROR", message=str(e))
        )
