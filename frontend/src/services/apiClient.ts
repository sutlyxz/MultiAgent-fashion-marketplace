/**
 * API Client Configuration and Base URL Helper
 *
 * Resolves the backend API base URL using `VITE_API_BASE_URL`:
 * - In production (e.g. deployed on Vercel): prepends `VITE_API_BASE_URL` (e.g. https://clothify-backend-0vii.onrender.com)
 * - In local development (empty/undefined): keeps relative `/api/...` paths to leverage Vite's dev server proxy
 * - Normalizes trailing slashes and avoids duplicate `/api/api` paths
 */

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";

/**
 * Normalized API Base URL without trailing slashes.
 */
export const API_BASE_URL: string = rawBaseUrl.trim().replace(/\/+$/, "");

/**
 * Resolves an API endpoint path against the configured base URL.
 *
 * @param endpoint - Relative endpoint path (e.g., "/api/products", "/api/auth/login")
 * @returns Fully qualified URL in production, or relative path in local dev
 */
export function apiUrl(endpoint: string): string {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  if (!API_BASE_URL) {
    return cleanEndpoint;
  }

  // Handle case where VITE_API_BASE_URL includes '/api' and endpoint also starts with '/api'
  if (API_BASE_URL.endsWith("/api") && cleanEndpoint.startsWith("/api/")) {
    return `${API_BASE_URL}${cleanEndpoint.slice(4)}`;
  }

  return `${API_BASE_URL}${cleanEndpoint}`;
}
