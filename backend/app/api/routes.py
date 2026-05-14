from fastapi import APIRouter
from app.models.schemas import InferenceRequest, LLMInferenceResponse, APIResponse, APIError
from app.pipelines.llm_only import run_llm_only_inference
from app.pipelines.basic_rag import run_basic_rag_inference
from app.pipelines.graphrag import run_graphrag_inference

router = APIRouter(prefix="/api/pipeline")

@router.post("/llm-only", response_model=APIResponse[LLMInferenceResponse])
async def llm_only_endpoint(request: InferenceRequest):
    try:
        result = await run_llm_only_inference(request)
        return APIResponse(status="success", data=result)
    except Exception as e:
        return APIResponse(status="error", error=APIError(code="PIPELINE_ERROR", message=str(e)))

@router.post("/basic-rag", response_model=APIResponse[LLMInferenceResponse])
async def basic_rag_endpoint(request: InferenceRequest):
    try:
        result = await run_basic_rag_inference(request)
        return APIResponse(status="success", data=result)
    except Exception as e:
        return APIResponse(status="error", error=APIError(code="PIPELINE_ERROR", message=str(e)))

@router.post("/graphrag", response_model=APIResponse[LLMInferenceResponse])
async def graphrag_endpoint(request: InferenceRequest):
    try:
        result = await run_graphrag_inference(request)
        return APIResponse(status="success", data=result)
    except Exception as e:
        return APIResponse(status="error", error=APIError(code="PIPELINE_ERROR", message=str(e)))
