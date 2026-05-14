import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PipelineCard from '../PipelineCard';

describe('PipelineCard', () => {
  it('renders title', () => {
    render(<PipelineCard title="Test Title" data={null} isLoading={false} error={null} />);
    expect(screen.getByText('Test Title')).toBeDefined();
  });

  it('renders loading state using Skeleton', () => {
    const { container } = render(<PipelineCard title="Test Title" data={null} isLoading={true} error={null} />);
    // Loading state content uses Skeleton
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('renders error state', () => {
    render(<PipelineCard title="Test Title" data={null} isLoading={false} error="Test Error" />);
    expect(screen.getByText(/Error: Test Error/i)).toBeDefined();
  });

  it('renders data', () => {
    const data = {
      answer: 'Graph answers are here.',
      metrics: {
        promptTokens: 100,
        completionTokens: 25,
        totalLatencyMs: 240,
        judgeScore: 'PASS' as const,
        bertScore: 0.91,
      }
    };
    render(<PipelineCard title="Test Title" data={data} isLoading={false} error={null} />);
    expect(screen.getByText(/Graph answers are here/i)).toBeDefined();
  });

  it('renders telemetry blocks firmly with formatting classes', () => {
    const data = {
      answer: 'Telemetry',
      metrics: {
        promptTokens: 100,
        completionTokens: 25,
        totalLatencyMs: 240,
        judgeScore: 'PASS' as const,
        bertScore: 0.91,
      }
    };
    const { container } = render(<PipelineCard title="Test Title" data={data} isLoading={false} error={null} />);
    const metricsBlock = container.querySelector('.font-mono.text-\\[13px\\]');
    expect(metricsBlock).not.toBeNull();
  });

  it('renders waiting state when no data, no error, and not loading', () => {
    render(<PipelineCard title="Test Title" data={null} isLoading={false} error={null} />);
    expect(screen.getByText('Waiting for execution...')).toBeDefined();
  });
});
