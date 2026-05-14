import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SummaryComparison from '../SummaryComparison';

describe('SummaryComparison Component', () => {
  const mockPipelines = {
    'llm-only': {
      title: 'LLM Only',
      data: { answer: 'A', metrics: { judgeScore: 'FAIL', promptTokens: 30, completionTokens: 20 } }
    },
    'vector-rag': {
      title: 'Vector RAG',
      data: { answer: 'B', metrics: { judgeScore: 'PASS', promptTokens: 100, completionTokens: 50 } }
    },
    graphrag: {
      title: 'GraphRAG',
      data: { answer: 'C', metrics: { judgeScore: 'PASS', promptTokens: 60, completionTokens: 40, bertScore: 0.91 } }
    }
  };

  it('renders the summary panel and crowns the winner', () => {
    render(<SummaryComparison pipelines={mockPipelines} />);
    
    expect(screen.getByText(/Winner: GraphRAG/i)).toBeDefined();
    expect(screen.getByText(/100 total/i)).toBeDefined();
  });

  it('renders nothing when there is no winner', () => {
    const { container } = render(<SummaryComparison pipelines={{}} />);
    expect(container.firstChild).toBeNull();
  });
});
