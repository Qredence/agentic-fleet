export interface ConversationStep {
  id: string;
  type:
    | "thought"
    | "status"
    | "reasoning"
    | "error"
    | "agent_start"
    | "agent_complete"
    | "agent_output"
    | "agent_thought"
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
    | "heartbeat";
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
}

/** Messages sent from client to server over WebSocket */
export type WebSocketClientMessage = ChatRequest | { type: "cancel" };

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
