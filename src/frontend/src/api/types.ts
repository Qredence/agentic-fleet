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
    | "agent_thought";
  content: string;
  timestamp: string;
  kind?: string; // e.g., 'routing', 'analysis', 'quality'
  data?: Record<string, unknown>;
  isExpanded?: boolean;
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
    | "agent.message";
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
}

export interface WorkflowSession {
  session_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface AgentInfo {
  name: string;
  description: string;
  capabilities?: string[];
}
