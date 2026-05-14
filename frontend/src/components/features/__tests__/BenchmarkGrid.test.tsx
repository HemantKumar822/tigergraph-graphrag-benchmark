import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BenchmarkGrid from '../BenchmarkGrid';
import * as usePipelineFetchModule from '@/hooks/usePipelineFetch';

// Mock the hook
vi.mock('@/hooks/usePipelineFetch', () => ({
  usePipelineFetch: vi.fn()
}));

describe('BenchmarkGrid', () => {
  const mockExecute1 = vi.fn();
  const mockExecute2 = vi.fn();
  const mockExecute3 = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    
    vi.mocked(usePipelineFetchModule.usePipelineFetch).mockImplementation((endpoint: string) => {
      if (endpoint === '/api/pipeline/llm-only') return { data: null, isLoading: false, error: null, execute: mockExecute1 };
      if (endpoint === '/api/pipeline/basic-rag') return { data: null, isLoading: false, error: null, execute: mockExecute2 };
      return { data: null, isLoading: false, error: null, execute: mockExecute3 };
    });
  });

  it('renders input fields for query, top_k, and num_hops', () => {
    render(<BenchmarkGrid />);
    
    expect(screen.getByPlaceholderText(/Compare token efficiency across architectures/i)).toBeDefined();
    expect(screen.getByLabelText(/top_k/i)).toBeDefined();
    expect(screen.getByLabelText(/num_hops/i)).toBeDefined();
  });

  it('dispatches parallel async HTTP requests on form submit', async () => {
    render(<BenchmarkGrid />);
    
    const queryInput = screen.getByPlaceholderText(/Compare token efficiency across architectures/i);
    const topKInput = screen.getByLabelText(/top_k/i);
    const numHopsInput = screen.getByLabelText(/num_hops/i);
    const submitBtn = screen.getByRole('button', { name: /Execute/i });

    fireEvent.change(queryInput, { target: { value: 'Test query' } });
    fireEvent.change(topKInput, { target: { value: '10' } });
    fireEvent.change(numHopsInput, { target: { value: '3' } });

    fireEvent.submit(submitBtn.closest('form')!);

    // Verify all 3 pipelines were called simultaneously with the same params
    const expectedParams = { top_k: 10, num_hops: 3 };
    expect(mockExecute1).toHaveBeenCalledWith('Test query', expectedParams);
    expect(mockExecute2).toHaveBeenCalledWith('Test query', expectedParams);
    expect(mockExecute3).toHaveBeenCalledWith('Test query', expectedParams);
  });

  it('renders three PipelineCards in a grid', () => {
    render(<BenchmarkGrid />);
    
    expect(screen.getByText(/LLM Only/i)).toBeDefined();
    expect(screen.getByText(/Vector RAG/i)).toBeDefined();
    expect(screen.getByText(/GraphRAG/i)).toBeDefined();
  });
});
