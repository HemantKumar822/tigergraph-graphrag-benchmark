import { renderHook, act } from '@testing-library/react';
import { usePipelineFetch } from '@/hooks/usePipelineFetch';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('usePipelineFetch', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = vi.fn();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => usePipelineFetch('/api/test'));
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should handle successful fetch', async () => {
    const mockData = { result: 'success' };
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'success', data: mockData }),
    } as Response);

    const { result } = renderHook(() => usePipelineFetch('/api/test'));
    
    await act(async () => {
      await result.current.execute('query', { top_k: 5, num_hops: 2 });
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('should handle failed fetch', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ status: 'error', error: { message: 'Internal Server Error' } }),
    } as Response);

    const { result } = renderHook(() => usePipelineFetch('/api/test'));
    
    await act(async () => {
      await result.current.execute('query', { top_k: 5, num_hops: 2 });
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Internal Server Error');
  });
});
