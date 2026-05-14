import { useState, useRef, useEffect } from 'react';
import { APIResponse } from '../types';

interface FetchParams {
  top_k: number;
  num_hops: number;
}

export function usePipelineFetch<T = unknown>(endpoint: string) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const execute = async (query: string, params: FetchParams) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          query,
          config: {
            top_k: params.top_k,
            num_hops: params.num_hops,
          }
        }),
      });

      const result = await response.json().catch(() => ({
        status: 'error',
        error: { code: 'PARSE_ERROR', message: 'Failed to parse server response.' }
      })) as APIResponse<T> | T | { error?: { message?: string } | string };

      const isEnvelope = typeof result === 'object' && result !== null && 'status' in result;

      if (!response.ok) {
        const message =
          isEnvelope
            ? (result as APIResponse<T>).error?.message
            : typeof (result as { error?: { message?: string } | string }).error === 'string'
              ? (result as { error: string }).error
              : (result as { error?: { message?: string } }).error?.message;
        throw new Error(message || `HTTP error! status: ${response.status}`);
      }

      if (isEnvelope && (result as APIResponse<T>).status === 'error') {
        throw new Error((result as APIResponse<T>).error?.message || 'Request failed');
      }

      const payload = (isEnvelope ? (result as APIResponse<T>).data : result) as T | null | undefined;
      setData(payload ?? null);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setData(null);
    } finally {
      if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
        setIsLoading(false);
      }
    }
  };

  return { data, isLoading, error, execute };
}
