import { describe, it, expect } from 'vitest';
import { determineWinner } from './winner';

describe('Winner Aggregator Logic', () => {
  it('identifies the winner with lowest tokens that has a PASS', () => {
    const pipelines = {
      pipelineA: { title: 'A', data: { answer: 'A', metrics: { judgeScore: 'PASS', promptTokens: 100, completionTokens: 50 } } },
      pipelineB: { title: 'B', data: { answer: 'B', metrics: { judgeScore: 'FAIL', promptTokens: 25, completionTokens: 25 } } },
      pipelineC: { title: 'C', data: { answer: 'C', metrics: { judgeScore: 'PASS', promptTokens: 60, completionTokens: 40 } } }
    };
    
    expect(determineWinner(pipelines)).toBe('pipelineC');
  });

  it('falls back to the lowest-token pipeline when no PASS verdict exists', () => {
    const pipelines = {
      pipelineA: { title: 'A', data: { answer: 'A', metrics: { judgeScore: 'FAIL', promptTokens: 100, completionTokens: 50 } } },
      pipelineB: { title: 'B', data: { answer: 'B', metrics: { judgeScore: 'FAIL', promptTokens: 25, completionTokens: 25 } } },
      pipelineC: { title: 'C', data: null }
    };
    
    expect(determineWinner(pipelines)).toBe('pipelineB');
  });
});
