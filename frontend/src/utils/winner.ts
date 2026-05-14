import { LLMInferenceResponse } from '../types';

export const determineWinner = (pipelines: Record<string, { data: LLMInferenceResponse | null, title: string }>): string | null => {
  let judgedWinner: string | null = null;
  let judgedMinTokens = Infinity;
  let fallbackWinner: string | null = null;
  let fallbackMinTokens = Infinity;

  Object.entries(pipelines).forEach(([key, pipeline]) => {
    const metrics = pipeline?.data?.metrics;
    if (!metrics) return;

    const totalTokens = (metrics?.promptTokens ?? 0) + (metrics?.completionTokens ?? 0);
    if (totalTokens <= 0) return;

    if (metrics?.judgeScore === 'PASS' && totalTokens > 0) {
      if (totalTokens < judgedMinTokens) {
        judgedMinTokens = totalTokens;
        judgedWinner = key;
      }
      return;
    }

    if (totalTokens < fallbackMinTokens && key !== 'llmOnly') {
      fallbackMinTokens = totalTokens;
      fallbackWinner = key;
    }
  });

  return judgedWinner ?? fallbackWinner;
};
