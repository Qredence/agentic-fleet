/**
 * API Module Index
 *
 * Re-exports all API-related modules for convenient imports.
 */

// Configuration
export {
  API_BASE_URL,
  API_PREFIX,
  STREAM_API_PREFIX,
  getStreamApiBase,
  getWebSocketUrl,
} from "./config";

// HTTP client
export { http, request, requestWithPrefix } from "./http";

// API clients
export {
  api,
  conversationsApi,
  sessionsApi,
  agentsApi,
  nluApi,
  optimizationApi,
  evaluationApi,
  improvementApi,
  sseApi,
  healthApi,
} from "./client";

// React Query hooks
export {
  queryKeys,
  useConversations,
  useConversation,
  useConversationMessages,
  useCreateConversation,
  useSessions,
  useSession,
  useCancelSession,
  useAgents,
  useHealthCheck,
  useReadinessCheck,
  useOptimizationRun,
  useOptimizationStatus,
  useEvaluationHistory,
  useInvalidateConversations,
} from "./hooks";

// Provider
export { QueryProvider } from "./QueryProvider";

// WebSocket service
export {
  ChatWebSocketService,
  getChatWebSocket,
  createChatWebSocket,
  type ConnectionStatus,
  type ChatWebSocketOptions,
  type ChatWebSocketCallbacks,
} from "./websocket";

// Types
export type {
  // Core types
  Message,
  MessageRole,
  Conversation,
  ConversationStep,
  StepCategory,
  UIHint,
  // Request/Response types
  ChatRequest,
  CreateConversationRequest,
  WebSocketClientMessage,
  ReasoningEffort,
  // Stream types
  StreamEvent,
  StreamEventType,
  // Session types
  WorkflowSession,
  WorkflowStatus,
  // Agent types
  AgentInfo,
  // NLU types
  IntentRequest,
  IntentResponse,
  EntityRequest,
  EntityResponse,
  // Optimization / Evaluation / Improvement types
  OptimizationRequest,
  OptimizationResult,
  HistoryExecutionEntry,
  HistoryQualityMetrics,
  SelfImproveRequest,
  SelfImproveResponse,
  SelfImproveStats,
  // Error types
  ApiError,
  // Tracing and Observability types
  Observation,
  TraceDetails,
} from "./types";

export { ApiRequestError } from "./types";
