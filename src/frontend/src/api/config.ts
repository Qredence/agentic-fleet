/**
 * API Configuration
 *
 * Centralized configuration for API endpoints and settings.
 */

/**
 * Get the API base URL from environment or use proxy fallback.
 * In development with Vite proxy, we use relative URLs ("/api/v1/...").
 * In production, this can be overridden via VITE_API_URL.
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "";

/**
 * API prefix for versioned endpoints.
 */
export const API_PREFIX = "/api/v1";

/**
 * WebSocket base URL - computed from window.location for proper protocol handling.
 */
export function getWebSocketUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  let host = window.location.host;
  if (API_BASE_URL) {
    try {
      host = new URL(API_BASE_URL).host;
    } catch {
      console.warn(
        `Invalid API_BASE_URL: ${API_BASE_URL}, falling back to window.location.host`,
      );
    }
  }
  return `${protocol}//${host}${path}`;
}
/**
 * API request timeout in milliseconds.
 */
export const API_TIMEOUT = 30000;

/**
 * Maximum retry attempts for failed requests.
 */
export const MAX_RETRIES = 3;

/**
 * Base delay for exponential backoff (in milliseconds).
 */
export const RETRY_BASE_DELAY = 1000;
