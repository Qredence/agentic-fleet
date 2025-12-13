/**
 * API Client
 *
 * High-level API client for AgenticFleet backend.
 * Uses the typed HTTP layer with retry logic and error handling.
 */

import { http } from "./http";
import type {
  Conversation,
  WorkflowSession,
  AgentInfo,
  Message,
  IntentRequest,
  IntentResponse,
  EntityRequest,
  EntityResponse,
  CreateConversationRequest,
} from "./types";

// =============================================================================
// Conversations API
// =============================================================================

export const conversationsApi = {
  /**
   * Create a new conversation.
   */
  create: (title: string = "New Chat") =>
    http.post<Conversation>("/conversations", {
      title,
    } satisfies CreateConversationRequest),

  /**
   * Get a conversation by ID.
   */
  get: (id: string) => http.get<Conversation>(`/conversations/${id}`),

  /**
   * List all conversations.
   */
  list: () => http.get<Conversation[]>("/conversations"),

  /**
   * Get messages for a conversation.
   */
  getMessages: async (id: string): Promise<Message[]> => {
    const conversation = await conversationsApi.get(id);
    return conversation.messages || [];
  },
};

// =============================================================================
// Sessions API
// =============================================================================

export const sessionsApi = {
  /**
   * List all workflow sessions.
   */
  list: () => http.get<WorkflowSession[]>("/sessions"),

  /**
   * Get a session by ID.
   */
  get: (id: string) => http.get<WorkflowSession>(`/sessions/${id}`),

  /**
   * Cancel a running session.
   */
  cancel: (id: string) => http.delete<void>(`/sessions/${id}`),
};

// =============================================================================
// Agents API
// =============================================================================

export const agentsApi = {
  /**
   * List all available agents.
   */
  list: () => http.get<AgentInfo[]>("/agents"),
};

// =============================================================================
// NLU API
// =============================================================================

export const nluApi = {
  /**
   * Classify user intent.
   */
  classifyIntent: (request: IntentRequest) =>
    http.post<IntentResponse>("/classify_intent", request),

  /**
   * Extract entities from text.
   */
  extractEntities: (request: EntityRequest) =>
    http.post<EntityResponse>("/extract_entities", request),
};

// =============================================================================
// Health API
// Note: Health endpoints are at root level, not under /api/v1
// =============================================================================

export interface HealthResponse {
  status: string;
  checks: Record<string, string>;
  version: string;
}

export interface ReadinessResponse {
  status: string;
  workflow: boolean;
}

/**
 * Direct fetch for health endpoints (bypass /api/v1 prefix).
 */
async function fetchHealth<T>(endpoint: string): Promise<T> {
  const response = await fetch(endpoint);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

export const healthApi = {
  /**
   * Check API health.
   */
  check: () => fetchHealth<HealthResponse>("/health"),

  /**
   * Check API readiness.
   */
  ready: () => fetchHealth<ReadinessResponse>("/ready"),
};

// =============================================================================
// Legacy API Object (for backward compatibility during migration)
// =============================================================================

export const api = {
  // NLU
  classifyIntent: nluApi.classifyIntent,
  extractEntities: nluApi.extractEntities,

  // Conversations
  createConversation: conversationsApi.create,
  getConversation: conversationsApi.get,
  listConversations: conversationsApi.list,
  loadConversationMessages: conversationsApi.getMessages,

  // Sessions
  listSessions: sessionsApi.list,
  getSession: sessionsApi.get,
  cancelSession: sessionsApi.cancel,

  // Agents
  listAgents: agentsApi.list,
};
