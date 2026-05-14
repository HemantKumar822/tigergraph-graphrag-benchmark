export const getBertScoreColor = (score: number): string => {
  return score >= 0.55 ? 'text-[#16a34a]' : 'text-[#eb8e90]';
};

export const getJudgeColor = (status: string): string => {
  return status === 'PASS' ? 'text-[#16a34a]' : 'text-[#eb8e90]';
};
