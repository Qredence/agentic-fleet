const DEFAULT_BACKEND_URL = "http://localhost:8000";

const normaliseBaseUrl = (value: string) => value.replace(/\/$/, "");

const getBackendBaseUrl = () =>
  normaliseBaseUrl(import.meta.env.VITE_BACKEND_URL ?? DEFAULT_BACKEND_URL);

export const API_ENDPOINTS = {
  CONVERSATIONS: "/v1/conversations",
  CONVERSATION_ITEMS: (conversationId: string) =>
    `/v1/conversations/${conversationId}/items`,
  APPROVALS: "/v1/approvals",
  APPROVAL_DECISION: (requestId: string) => `/v1/approvals/${requestId}`,
  CHAT: "/v1/chat",
  HEALTH: "/health",
} as const;

export type ApiEndpointKey = keyof typeof API_ENDPOINTS;

export const buildApiUrl = (path: string): string => {
  const base = getBackendBaseUrl();
  if (!path.startsWith("/")) {
    return `${base}/${path}`;
  }
  return `${base}${path}`;
};
