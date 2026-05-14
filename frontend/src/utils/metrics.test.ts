import { describe, it, expect } from 'vitest';
import { getBertScoreColor, getJudgeColor } from './metrics';

describe('metrics formatting', () => {
  it('getBertScoreColor returns green for score >= 0.55', () => {
    expect(getBertScoreColor(0.55)).toBe('text-[#16a34a]');
    expect(getBertScoreColor(0.99)).toBe('text-[#16a34a]');
  });

  it('getBertScoreColor returns red for score < 0.55', () => {
    expect(getBertScoreColor(0.54)).toBe('text-[#eb8e90]');
    expect(getBertScoreColor(0.1)).toBe('text-[#eb8e90]');
  });

  it('getJudgeColor returns green for PASS', () => {
    expect(getJudgeColor('PASS')).toBe('text-[#16a34a]');
  });

  it('getJudgeColor returns red for FAIL', () => {
    expect(getJudgeColor('FAIL')).toBe('text-[#eb8e90]');
  });
});
