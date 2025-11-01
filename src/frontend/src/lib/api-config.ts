/**
 * API Configuration
 *
 * Centralized configuration for FastAPI backend endpoints
 */

/**
 * Get the API base URL from environment or use default
 */
const getApiBaseUrl = (): string => {
  // Check Vite environment variables
  const envApiUrl = import.meta.env.VITE_API_URL;
  if (envApiUrl) {
    return envApiUrl;
  }

  // Default to localhost:8000 for development
  return "http://localhost:8000";
};

/**
 * API endpoint paths (without base URL)
 */
export const API_ENDPOINTS = {
  HEALTH: "/v1/system/health",
  CONVERSATIONS: "/v1/conversations",
  RESPONSES: "/v1/responses",
  APPROVALS: "/v1/approvals",
  APPROVAL_RESPONSE: (requestId: string) =>
    `/v1/approvals/${requestId}/respond`,
  CONVERSATION_MESSAGES: (conversationId: string) =>
    `/v1/conversations/${conversationId}`,
} as const;

/**
 * Build a full API URL from an endpoint path
 */
export function buildApiUrl(endpoint: string): string {
  const baseUrl = getApiBaseUrl();
  // Ensure no double slashes when joining
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedEndpoint = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;
  return `${normalizedBase}${normalizedEndpoint}`;
}

/**
 * Export the base URL getter for direct use if needed
 */
export { getApiBaseUrl };
