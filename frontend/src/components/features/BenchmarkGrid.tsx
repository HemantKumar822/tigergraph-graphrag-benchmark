import React, { useState } from 'react';
import { usePipelineFetch } from '@/hooks/usePipelineFetch';
import PipelineCard from './PipelineCard';
import SummaryComparison from './SummaryComparison';
import { LLMInferenceResponse } from '@/types';

export default function BenchmarkGrid() {
  const [query, setQuery] = useState('');
  const [groundTruth, setGroundTruth] = useState('');
  const [topK, setTopK] = useState<number | ''>(5);
  const [numHops, setNumHops] = useState<number | ''>(2);

  // Pointing explicitly to consistent backend routes prefixed under /api/pipeline
  const llmPipeline = usePipelineFetch<LLMInferenceResponse>('/api/pipeline/llm-only');
  const vectorRagPipeline = usePipelineFetch<LLMInferenceResponse>('/api/pipeline/basic-rag');
  const graphRagPipeline = usePipelineFetch<LLMInferenceResponse>('/api/pipeline/graphrag');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const cleanTopK = Math.min(20, Math.max(1, typeof topK === 'number' && !isNaN(topK) ? topK : 5));
    const cleanNumHops = Math.min(5, Math.max(1, typeof numHops === 'number' && !isNaN(numHops) ? numHops : 2));

    const params = { top_k: cleanTopK, num_hops: cleanNumHops, ground_truth: groundTruth.trim() || undefined };
    
    llmPipeline.execute(query, params);
    vectorRagPipeline.execute(query, params);
    graphRagPipeline.execute(query, params);
  };

  // Construct collective pipeline map for visual winner comparison logic
  const aggregatePipelines = {
    'llm-only': { data: llmPipeline.data, title: 'LLM Only' },
    'vector-rag': { data: vectorRagPipeline.data, title: 'Vector RAG' },
    'graphrag': { data: graphRagPipeline.data, title: 'GraphRAG' },
  };

  // Check if any of the pipelines completed to render the winner summary
  const hasAnyFinished = !!(llmPipeline.data || vectorRagPipeline.data || graphRagPipeline.data);

  return (
    <div id="benchmark-grid" className="w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8">
      {/* Control Panel */}
      <form onSubmit={handleSubmit} className="bg-white border border-[#f0f0f3] rounded-[12px] p-6 mb-8 shadow-sm">
        <div className="flex flex-col md:flex-row flex-wrap gap-4 items-end">
          <div className="flex-1 w-full">
            <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-1">
              Natural Language Query
            </label>
            <input
              id="query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Compare token efficiency across architectures..."
              className="w-full px-4 py-2 border border-[#f0f0f3] rounded-md focus:ring-2 focus:ring-[#0d74ce] focus:border-[#0d74ce] outline-none text-[#171717]"
            />
          </div>
          
          <div className="flex-1 w-full mt-4 md:mt-0">
            <label htmlFor="groundTruth" className="block text-sm font-medium text-gray-700 mb-1">
              Ground Truth (For Evaluation)
            </label>
            <input
              id="groundTruth"
              type="text"
              value={groundTruth}
              onChange={(e) => setGroundTruth(e.target.value)}
              placeholder="Optional: Text to evaluate BERT and Judge against..."
              className="w-full px-4 py-2 border border-blue-200 bg-blue-50/30 rounded-md focus:ring-2 focus:ring-[#0d74ce] focus:border-[#0d74ce] outline-none text-[#171717]"
            />
          </div>
          
          <div className="w-full md:w-32">
            <label htmlFor="topK" className="block text-sm font-medium text-gray-700 mb-1">
              top_k
            </label>
            <input
              id="topK"
              type="number"
              min="1"
              max="20"
              value={topK === '' ? '' : topK}
              onChange={(e) => {
                const val = e.target.value;
                setTopK(val === '' ? '' : parseInt(val, 10));
              }}
              className="w-full px-4 py-2 border border-[#f0f0f3] rounded-md focus:ring-2 focus:ring-[#0d74ce] focus:border-[#0d74ce] outline-none text-[#171717]"
            />
          </div>
          
          <div className="w-full md:w-32">
            <label htmlFor="numHops" className="block text-sm font-medium text-gray-700 mb-1">
              num_hops
            </label>
            <input
              id="numHops"
              type="number"
              min="1"
              max="5"
              value={numHops === '' ? '' : numHops}
              onChange={(e) => {
                const val = e.target.value;
                setNumHops(val === '' ? '' : parseInt(val, 10));
              }}
              className="w-full px-4 py-2 border border-[#f0f0f3] rounded-md focus:ring-2 focus:ring-[#0d74ce] focus:border-[#0d74ce] outline-none text-[#171717]"
            />
          </div>

          <button
            type="submit"
            disabled={llmPipeline.isLoading || vectorRagPipeline.isLoading || graphRagPipeline.isLoading}
            className="w-full md:w-auto flex h-[40px] items-center justify-center gap-2 rounded-md bg-[#000000] px-8 text-sm font-semibold tracking-tight text-white transition-colors hover:bg-[#1a1a1a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#000000] disabled:opacity-50"
          >
            {(llmPipeline.isLoading || vectorRagPipeline.isLoading || graphRagPipeline.isLoading) ? 'Running...' : 'Execute'}
          </button>
        </div>
      </form>

      {/* Show quantitative winner comparison when data exists */}
      {hasAnyFinished && (
        <div className="mb-8">
          <SummaryComparison pipelines={aggregatePipelines} />
        </div>
      )}

      {/* Grid of Results */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[500px]">
        <PipelineCard
          title="LLM Only"
          data={llmPipeline.data}
          isLoading={llmPipeline.isLoading}
          error={llmPipeline.error}
        />
        <PipelineCard
          title="Vector RAG"
          data={vectorRagPipeline.data}
          isLoading={vectorRagPipeline.isLoading}
          error={vectorRagPipeline.error}
        />
        <PipelineCard
          title="GraphRAG"
          data={graphRagPipeline.data}
          isLoading={graphRagPipeline.isLoading}
          error={graphRagPipeline.error}
        />
      </div>
    </div>
  );
}
