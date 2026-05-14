export interface APIError {
  code: string;
  message: string;
}

export interface APIResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: APIError;
}

export interface PipelineMetrics {
  promptTokens: number;
  completionTokens: number;
  latencyMs?: number;
  semanticSearchLatencyMs?: number;
  graphTraversalLatencyMs?: number;
  totalLatencyMs?: number;
  judgeScore?: 'PASS' | 'FAIL' | 'N/A';
  bertScore?: number;
}

export interface LLMInferenceResponse {
  answer: string;
  metrics: PipelineMetrics;
}

export interface PipelineResult {
  status: 'success' | 'error';
  data?: LLMInferenceResponse;
  error?: string;
}

export interface BenchmarkResults {
  llmOnly: PipelineResult;
  basicRag: PipelineResult;
  graphRag: PipelineResult;
}

export interface BenchmarkResponse {
  results: BenchmarkResults;
}
