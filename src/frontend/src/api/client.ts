/**
 * API Client
 *
 * High-level API client for AgenticFleet backend.
 * Uses the typed HTTP layer with retry logic and error handling.
 */

import { http, requestWithPrefix } from "@/api/http";
import { getStreamApiBase } from "./config";
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
  OptimizationRequest,
  OptimizationResult,
  HistoryExecutionEntry,
  DSPyConfig,
  DSPyStats,
  CacheInfo,
  ReasonerSummary,
  DSPySignatures,
  DSPyPrompts,
  TraceDetails,
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
  list: (params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined)
      query.set("offset", String(params.offset));
    return http.get<Conversation[]>(`/conversations?${query.toString()}`);
  },

  /**
   * Get messages for a conversation.
   */
  getMessages: async (id: string): Promise<Message[]> => {
    const conversation = await conversationsApi.get(id);
    return conversation.messages || [];
  },

  /**
   * Delete a conversation by ID.
   */
  delete: (id: string) => http.delete(`/conversations/${id}`),
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
// Optimization API
// =============================================================================

export const optimizationApi = {
  /**
   * Start an optimization/compilation run.
   */
  run: (request: OptimizationRequest) =>
    http.post<OptimizationResult>("/optimization/jobs", request),

  /**
   * Get status for an optimization job.
   */
  status: (jobId: string) =>
    http.get<OptimizationResult>(
      `/optimization/jobs/${encodeURIComponent(jobId)}`,
    ),
};

// =============================================================================
// Evaluation API (History)
// =============================================================================

export const evaluationApi = {
  /**
   * Retrieve execution history (newest first).
   */
  history: (params?: { limit?: number; offset?: number }) => {
    const limit = params?.limit ?? 20;
    const offset = params?.offset ?? 0;
    return http.get<HistoryExecutionEntry[]>(
      `/history?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`,
    );
  },
};

// =============================================================================
// SSE API
// =============================================================================

export const sseApi = {
  /**
   * Cancel a running SSE workflow.
   */
  cancel: (conversationId: string, workflowId: string) => {
    const params = new URLSearchParams({ workflow_id: workflowId });
    return requestWithPrefix<void>(
      getStreamApiBase(),
      `/chat/${encodeURIComponent(conversationId)}/cancel?${params.toString()}`,
      { method: "POST" },
    );
  },

  /**
   * Submit a human-in-the-loop response.
   */
  submitResponse: (
    conversationId: string,
    workflowId: string,
    requestId: string,
    response: unknown,
  ) => {
    const params = new URLSearchParams({ workflow_id: workflowId });
    return requestWithPrefix<void>(
      getStreamApiBase(),
      `/chat/${encodeURIComponent(conversationId)}/respond?${params.toString()}`,
      {
        method: "POST",
        body: {
          request_id: requestId,
          response,
        },
      },
    );
  },
};

// =============================================================================
// DSPy Management API
// =============================================================================

export const dspyApi = {
  /**
   * Get DSPy predictor prompts and demos.
   */
  getPrompts: () => http.get<DSPyPrompts>("/dspy/prompts"),

  /**
   * Get current DSPy configuration.
   */
  getConfig: () => http.get<DSPyConfig>("/dspy/config"),

  /**
   * Get DSPy usage statistics.
   */
  getStats: () => http.get<DSPyStats>("/dspy/stats"),

  /**
   * Get DSPy compilation cache information.
   */
  getCacheInfo: () => http.get<CacheInfo>("/dspy/cache"),

  /**
   * Clear DSPy compilation cache.
   */
  clearCache: () => http.delete<void>("/dspy/cache"),

  /**
   * Get DSPy reasoner summary (routing cache, typed signatures).
   */
  getReasonerSummary: () => http.get<ReasonerSummary>("/dspy/reasoner/summary"),

  /**
   * Clear DSPy routing decision cache.
   */
  clearRoutingCache: () => http.delete<void>("/dspy/reasoner/routing-cache"),

  /**
   * List all available DSPy signatures.
   */
  getSignatures: () => http.get<DSPySignatures>("/dspy/signatures"),
};

// =============================================================================
// Observability API
// =============================================================================

export const observabilityApi = {
  /**
   * Fetch full trace details for a workflow.
   */
  getTrace: (workflowId: string) =>
    http.get<TraceDetails>(
      `/observability/trace/${encodeURIComponent(workflowId)}`,
    ),

  /**
   * List recent workflow traces.
   */
  listTraces: (params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined)
      query.set("offset", String(params.offset));
    return http.get<TraceDetails[]>(
      `/observability/traces?${query.toString()}`,
    );
  },
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

  // Optimization / Evaluation
  optimize: optimizationApi.run,
  optimizeStatus: optimizationApi.status,
  history: evaluationApi.history,

  // DSPy Management
  dspyPrompts: dspyApi.getPrompts,
  dspyConfig: dspyApi.getConfig,
  dspyStats: dspyApi.getStats,
  dspyCacheInfo: dspyApi.getCacheInfo,
  dspyClearCache: dspyApi.clearCache,
  dspyReasonerSummary: dspyApi.getReasonerSummary,
  dspyClearRoutingCache: dspyApi.clearRoutingCache,
  dspySignatures: dspyApi.getSignatures,

  // Observability
  getTrace: observabilityApi.getTrace,
  listTraces: observabilityApi.listTraces,
};
