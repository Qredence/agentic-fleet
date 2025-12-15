export interface ConversationStep {
  id: string;
  type:
    | "thought"
    | "status"
    | "request"
    | "reasoning"
    | "error"
    | "agent_start"
    | "agent_complete"
    | "agent_output"
    | "agent_thought"
    | "agent_message"
    | "routing"
    | "analysis"
    | "quality"
    | "handoff"
    | "tool_call"
    | "progress";
  content: string;
  timestamp: string;
  kind?: string; // e.g., 'routing', 'analysis', 'quality'
  data?: Record<string, unknown>;
  isExpanded?: boolean;
  category?:
    | "step"
    | "thought"
    | "reasoning"
    | "planning"
    | "output"
    | "response"
    | "status"
    | "error";
  uiHint?: {
    component: string;
    priority: "low" | "medium" | "high";
    collapsible: boolean;
    iconHint?: string;
  };
}

export interface Message {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  agent_id?: string;
  author?: string;
  steps?: ConversationStep[];
  /** Group ID for consecutive messages from the same agent */
  groupId?: string;
  /** Whether this message is a workflow placeholder (contains only events, no content yet) */
  isWorkflowPlaceholder?: boolean;
  /** Current workflow phase for shimmer display (e.g., "Routing...", "Executing...") */
  workflowPhase?: string;
  qualityFlag?: string;
  qualityScore?: number;
  /** Narrative summary of the execution */
  narrative?: string;
  /** Whether this was a fast path execution */
  isFast?: boolean;
  /** Execution latency */
  latency?: string;
  /** Completed workflow phases for this message */
  completedPhases?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
  stream?: boolean;
  /** Per-request reasoning effort override for GPT-5 models */
  reasoning_effort?: "minimal" | "medium" | "maximal";
  /**
   * Enable workflow checkpoint persistence for this new run.
   *
   * This is separate from resume. To resume a previously checkpointed workflow,
   * send a `workflow.resume` message with a `checkpoint_id`.
   */
  enable_checkpointing?: boolean;
  /**
   * Optional checkpoint identifier for resuming a previously checkpointed workflow.
   *
   * Do not set this for normal chat requests (new runs). In agent-framework, `message` and
   * `checkpoint_id` are mutually exclusive.
   *
   * @deprecated Prefer `enable_checkpointing` for new runs and `workflow.resume` for resume.
   */
  checkpoint_id?: string;
}

export interface WorkflowResumeRequest {
  type: "workflow.resume";
  conversation_id?: string;
  checkpoint_id: string;
  stream?: boolean;
  /** Per-request reasoning effort override for GPT-5 models */
  reasoning_effort?: "minimal" | "medium" | "maximal";
}

export interface CancelRequest {
  type: "cancel";
}

export interface WorkflowResponseRequest {
  type: "workflow.response";
  request_id: string;
  response: unknown;
}

export interface CreateConversationRequest {
  title?: string;
}

export interface StreamEvent {
  type:
    | "response.delta"
    | "response.completed"
    | "error"
    | "orchestrator.message"
    | "orchestrator.thought"
    | "reasoning.delta"
    | "reasoning.completed"
    | "done"
    | "agent.start"
    | "agent.complete"
    | "agent.output"
    | "agent.thought"
    | "agent.message"
    | "connected"
    | "cancelled"
    | "heartbeat"
    | "workflow.status";
  delta?: string;
  agent_id?: string;
  author?: string;
  role?: "user" | "assistant" | "system";
  content?: string;
  message?: string;
  error?: string;
  reasoning?: string;
  kind?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
  /** True if reasoning was interrupted mid-stream (on error events) */
  reasoning_partial?: boolean;
  /** Heuristic quality score/flag from backend for final answers */
  quality_score?: number;
  quality_flag?: string;
  /** Category of the event for UI grouping */
  category?: string;
  /** UI rendering hints from the backend */
  ui_hint?: {
    component: string;
    priority: "low" | "medium" | "high";
    collapsible: boolean;
    icon_hint?: string;
  };
  /** Optional workflow identifier for correlating logs */
  workflow_id?: string;
  /** Terminal-friendly log line mirrored from the backend logger */
  log_line?: string;
  /** Workflow status (for workflow.status events) */
  status?: "in_progress" | "failed" | "idle" | "completed";
}

/** Messages sent from client to server over WebSocket */
export type WebSocketClientMessage =
  | ChatRequest
  | WorkflowResumeRequest
  | CancelRequest
  | WorkflowResponseRequest;

export interface WorkflowSession {
  workflow_id: string;
  task: string;
  status: "created" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  started_at?: string;
  completed_at?: string;
  reasoning_effort?: string;
}

export interface AgentInfo {
  name: string;
  description: string;
  type: string;
}

export interface IntentRequest {
  text: string;
  possible_intents: string[];
}

export interface IntentResponse {
  intent: string;
  confidence: number;
  reasoning: string;
}

export interface EntityRequest {
  text: string;
  entity_types: string[];
}

export interface EntityResponse {
  entities: {
    text: string;
    type: string;
    confidence: string;
  }[];
  reasoning: string;
}

// =============================================================================
// Optimization / Evaluation / Self-Improvement Types
// =============================================================================

export interface OptimizationRequest {
  optimizer?: "bootstrap" | "gepa";
  use_cache?: boolean;
  gepa_auto?: "light" | "medium" | "heavy" | null;
  harvest_history?: boolean;
  min_quality?: number;
}

export interface OptimizationResult {
  status: "started" | "running" | "completed" | "cached" | "failed";
  job_id?: string | null;
  message: string;
  cache_path?: string | null;
  started_at?: string;
  completed_at?: string;
  error?: string;
  progress?: number;
  details?: Record<string, unknown>;
}

export interface HistoryQualityMetrics {
  score?: number;
  flag?: string;
  improvements?: string;
}

export interface HistoryExecutionEntry {
  workflowId?: string;
  workflow_id?: string;
  task?: string;
  status?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  latency?: string | number;
  mode?: string;
  routing?: Record<string, unknown>;
  quality?: HistoryQualityMetrics;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SelfImproveRequest {
  min_quality?: number;
  max_examples?: number;
  stats_only?: boolean;
}

export interface SelfImproveStats {
  total_executions?: number;
  high_quality_executions?: number;
  potential_new_examples?: number;
  min_quality_threshold?: number;
  average_quality_score?: number;
  quality_score_distribution?: Record<string, number>;
  [key: string]: unknown;
}

export interface SelfImproveResponse {
  status: "completed" | "no_op" | "failed";
  message: string;
  new_examples_added?: number;
  stats?: SelfImproveStats;
  details?: Record<string, unknown>;
}

// =============================================================================
// DSPy Management Types
// =============================================================================

export interface DSPyConfig {
  lm_provider: string;
  adapter: string;
}

export interface DSPyStats {
  history_count: number;
}

export interface CacheInfo {
  exists: boolean;
  created_at?: string;
  cache_size_bytes?: number;
  optimizer?: string;
  signature_hash?: string;
}

export interface ReasonerSummary {
  history_count: number;
  routing_cache_size: number;
  use_typed_signatures: boolean;
  modules_initialized: boolean;
}

export interface SignatureFieldInfo {
  name: string;
  desc: string;
  prefix: string;
}

export interface SignatureInfo {
  name: string;
  type: string;
  instructions?: string;
  input_fields: string[];
  output_fields: string[];
}

export interface PredictorPromptInfo {
  instructions: string;
  inputs: SignatureFieldInfo[];
  outputs: SignatureFieldInfo[];
  demos_count: number;
  demos: Record<string, string>[];
}

export type DSPySignatures = Record<string, SignatureInfo>;
export type DSPyPrompts = Record<string, PredictorPromptInfo>;

// =============================================================================
// Exported Type Aliases for Convenience
// =============================================================================

export type MessageRole = "user" | "assistant" | "system";
export type ReasoningEffort = "minimal" | "medium" | "maximal";
export type WorkflowStatus =
  | "created"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";
export type StreamEventType = StreamEvent["type"];

export type StepCategory =
  | "step"
  | "thought"
  | "reasoning"
  | "planning"
  | "output"
  | "response"
  | "status"
  | "error";

export interface UIHint {
  component: string;
  priority: "low" | "medium" | "high";
  collapsible: boolean;
  iconHint?: string;
}

// =============================================================================
// API Error Types
// =============================================================================

export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, unknown>;
}

export class ApiRequestError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.status = error.status;
    this.code = error.code;
    this.details = error.details;
  }
}
