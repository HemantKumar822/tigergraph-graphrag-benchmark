import React from 'react';
import { LLMInferenceResponse } from '../../types';

interface SummaryComparisonProps {
  pipelines: Record<string, { data: LLMInferenceResponse | null, title: string }>;
}

export default function SummaryComparison({ pipelines }: SummaryComparisonProps) {
  // Collect all completed pipelines with their metrics
  const pipelineResults = Object.entries(pipelines)
    .filter(([_, p]) => p.data?.metrics)
    .map(([key, p]) => {
      const metrics = p.data!.metrics;
      const totalTokens = metrics.promptTokens + metrics.completionTokens;
      return {
        key,
        title: p.title,
        totalTokens,
        promptTokens: metrics.promptTokens,
        completionTokens: metrics.completionTokens,
        bertScore: metrics.bertScore,
        judgeScore: metrics.judgeScore,
        latency: metrics.latency,
      };
    });

  if (pipelineResults.length === 0) return null;

  // Sort by token efficiency (ascending = better efficiency)
  const sorted = [...pipelineResults].sort((a, b) => a.totalTokens - b.totalTokens);

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-[12px] p-6 mb-8 shadow-sm">
      <h2 className="text-lg font-bold text-blue-900 mb-4 flex items-center gap-2">
        📊 Pipeline Comparison Rankings
      </h2>
      
      <div className="space-y-3">
        {sorted.map((result, rank) => (
          <div key={result.key} className={`border rounded-lg p-4 flex items-center justify-between ${
            rank === 0 ? 'bg-green-50 border-green-300' : rank === 1 ? 'bg-blue-50 border-blue-300' : 'bg-gray-50 border-gray-200'
          }`}>
            <div className="flex items-center gap-4 flex-1">
              <div className="text-2xl font-black w-8 text-center">
                {rank === 0 ? '🥇' : rank === 1 ? '🥈' : '🥉'}
              </div>
              <div className="flex-1">
                <div className="font-bold text-gray-900">{result.title}</div>
                <div className="text-xs text-gray-600 mt-1">
                  <span className="inline-block mr-3">📝 {result.totalTokens.toLocaleString()} total tokens</span>
                  <span className="inline-block mr-3">({result.promptTokens.toLocaleString()} prompt / {result.completionTokens.toLocaleString()} completion)</span>
                  {result.latency && <span className="inline-block">⏱️ {(result.latency / 1000).toFixed(2)}s</span>}
                </div>
              </div>
            </div>

            {/* Quality Metrics */}
            <div className="flex gap-4 ml-4 text-sm">
              {result.bertScore !== undefined && result.bertScore !== null && (
                <div className="text-center">
                  <div className="text-[10px] text-gray-600 font-semibold">BERTScore</div>
                  <div className="font-bold text-emerald-600">{result.bertScore.toFixed(3)}</div>
                </div>
              )}
              {result.judgeScore !== undefined && result.judgeScore !== null && (
                <div className="text-center">
                  <div className="text-[10px] text-gray-600 font-semibold">Judge</div>
                  <div className="font-bold text-purple-600">{result.judgeScore.toFixed(1)}/10</div>
                </div>
              )}
              {!result.bertScore && !result.judgeScore && (
                <div className="text-xs text-gray-400 italic">Provide ground truth to see quality metrics</div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-white border border-blue-100 rounded-md text-xs text-gray-700">
        <strong>💡 How to read:</strong> Lower token count = more efficient. With ground truth: Higher BERTScore (0-1) and Judge score (0-10) = better quality.
      </div>
    </div>
  );
}
