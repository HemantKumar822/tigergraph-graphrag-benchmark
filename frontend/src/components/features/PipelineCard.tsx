import React from 'react';
import { Skeleton } from '../ui/Skeleton';
import { LLMInferenceResponse } from '../../types';

interface PipelineCardProps {
  title: string;
  data: LLMInferenceResponse | null;
  isLoading: boolean;
  error: string | null;
}

export default function PipelineCard({ title, data, isLoading, error }: PipelineCardProps) {
  return (
    <div className="border border-[#f0f0f3] rounded-[12px] p-6 bg-white shadow-sm flex flex-col h-full min-h-[300px]">
      <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>
      
      <div className="flex-1 overflow-auto flex flex-col">
        {isLoading && (
          <div className="flex flex-col gap-3 py-2 w-full h-full">
             <Skeleton className="h-6 w-3/4" />
             <Skeleton className="h-4 w-full" />
             <Skeleton className="h-4 w-5/6" />
             <div className="mt-auto">
                <Skeleton className="h-20 w-full" />
             </div>
          </div>
        )}
        
        {error && (
          <div className="text-red-500 bg-red-50 p-3 rounded-md font-medium text-sm">
            Error: {error}
          </div>
        )}
        
        {!isLoading && !error && data && (
          <div className="flex flex-col h-full gap-4">
            <div className="text-sm bg-gray-50 p-4 rounded-md border border-gray-100 flex-1 text-gray-800 leading-relaxed whitespace-pre-wrap overflow-y-auto max-h-[240px]">
              {data.answer}
            </div>
            {data.metrics && (
               <div className="bg-[#1e1e1e] border border-[#333333] p-4 rounded-md font-mono text-[13px] mt-auto flex flex-col gap-3 shadow-inner">
                 <div className="font-semibold text-[#888888] uppercase tracking-wider text-[11px]">Telemetry & Metrics</div>
                 <div className="flex flex-col gap-2">
                   <div className="flex justify-between items-center pb-2 border-b border-[#333333]">
                     <span className="text-[#a0a0a0]">Tokens (P/C)</span>
                     <span className="text-white font-medium">{data.metrics.promptTokens} / {data.metrics.completionTokens}</span>
                   </div>
                   <div className="flex justify-between items-center pb-2 border-b border-[#333333]">
                     <span className="text-[#a0a0a0]">Latency</span>
                     <span className="text-white font-medium">{(data.metrics.totalLatencyMs || data.metrics.latencyMs || 0).toFixed(0)} ms</span>
                   </div>
                   <div className="flex justify-between items-center pb-2 border-b border-[#333333]">
                     <span className="text-[#a0a0a0]">Est. Cost</span>
                     <span className="text-white font-medium">${((data.metrics.promptTokens * 0.00000015) + (data.metrics.completionTokens * 0.00000060)).toFixed(6)}</span>
                   </div>
                   <div className="flex justify-between items-center pt-1">
                     <span className="text-[#a0a0a0]">Judge / BERT</span>
                     <div className="flex gap-2">
                       <span className={`px-2 py-0.5 rounded-sm bg-[#2a2a2a] border border-[#444444] font-bold ${data.metrics.judgeScore === 'PASS' ? 'text-[#16a34a]' : 'text-[#eb8e90]'}`}>
                         {data.metrics.judgeScore || 'N/A'}
                       </span>
                       <span className={`px-2 py-0.5 rounded-sm bg-[#2a2a2a] border border-[#444444] font-bold ${(data.metrics.bertScore || 0) >= 0.55 ? 'text-[#16a34a]' : 'text-[#eb8e90]'}`}>
                         {data.metrics.bertScore !== undefined && data.metrics.bertScore !== null ? data.metrics.bertScore.toFixed(3) : 'N/A'}
                       </span>
                     </div>
                   </div>
                 </div>
               </div>
            )}
          </div>
        )}
        
        {!isLoading && !error && !data && (
          <div className="flex flex-col items-center justify-center flex-1 text-gray-400 italic">
            <div className="mb-2 text-3xl opacity-20">⚡</div>
            Waiting for execution...
          </div>
        )}
      </div>
    </div>
  );
}
