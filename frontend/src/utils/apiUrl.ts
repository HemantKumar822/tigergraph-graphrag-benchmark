/**
 * Dynamically resolves relative /api paths into direct backend addresses
 * running on the host machine's browser execution context.
 * Bypasses brittle server-side Next.js container proxies.
 */
export function getApiUrl(path: string): string {
  if (typeof window === 'undefined') {
    // Fallback for server-side generation (SSG / SSR) within the container network
    return `http://backend:8080${path}`;
  }
  
  // Client-side browser context: map back to the user's browser host on 8080
  const host = window.location.hostname || 'localhost';
  return `http://${host}:8080${path}`;
}
