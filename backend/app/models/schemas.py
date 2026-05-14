from typing import Generic, TypeVar, Optional, Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")

class BaseCamelModel(BaseModel):
    """
    Base model that enforces camelCase keys in JSON output,
    matching the frontend TypeScript expectations.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )

class APIError(BaseCamelModel):
    code: str
    message: str

class APIResponse(BaseCamelModel, Generic[T]):
    """
    Standardized API Envelope for ALL endpoints.
    """
    status: str
    data: Optional[T] = None
    error: Optional[APIError] = None

class InferenceConfig(BaseCamelModel):
    temperature: Optional[float] = Field(0.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(1024, ge=1, le=8192)
    top_k: Optional[int] = Field(5, ge=1, le=50)
    num_hops: Optional[int] = Field(2, ge=1, le=10)

class InferenceRequest(BaseCamelModel):
    query: str = Field(..., min_length=1, max_length=10000)
    ground_truth: Optional[str] = None
    config: Optional[InferenceConfig] = None

class PipelineMetrics(BaseCamelModel):
    prompt_tokens: int
    completion_tokens: int
    latency_ms: Optional[float] = None
    semantic_search_latency_ms: Optional[float] = None
    graph_traversal_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    judge_score: Optional[Literal["PASS", "FAIL", "N/A"]] = None
    bert_score: Optional[float] = None

class LLMInferenceResponse(BaseCamelModel):
    answer: str
    metrics: PipelineMetrics

class PipelineResult(BaseCamelModel):
    """
    Wraps a single pipeline outcome — either a successful LLMInferenceResponse
    or an error string. This allows the orchestrator to return partial results
    when one pipeline fails without aborting the entire benchmark run.
    """
    status: Literal["success", "error"]  # enforced by schema
    data: Optional[LLMInferenceResponse] = None
    error: Optional[str] = None

class BenchmarkResults(BaseCamelModel):
    llm_only: PipelineResult
    basic_rag: PipelineResult
    graph_rag: PipelineResult

class BenchmarkResponse(BaseCamelModel):
    results: BenchmarkResults
