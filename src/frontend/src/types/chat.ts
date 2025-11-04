/** Chat message roles */
export type MessageRole = "user" | "assistant" | "system";

/** Chat message structure */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: number;
  agentId?: string;
}

/** SSE Event types from backend */
export type SSEEventType =
  | "response.delta"
  | "response.completed"
  | "orchestrator.message"
  | "agent.message.complete"
  | "error";

/** SSE Event structure
 * Backend events emit `agent_id`; the frontend normalises to camelCase `agentId`
 * inside `streamChatResponse` before state updates.
 */
export interface SSEEvent {
  type: SSEEventType;
  delta?: string;
  agentId?: string;
  error?: string;
  message?: string;
  kind?: string;
  content?: string;
}

/** Response delta event */
export interface ResponseDeltaEvent {
  type: "response.delta";
  delta: string;
  agentId?: string;
}

/** Response completed event */
export interface ResponseCompletedEvent {
  type: "response.completed";
}

/** Orchestrator message event */
export interface OrchestratorMessageEvent {
  type: "orchestrator.message";
  message: string;
  kind?: string;
}

export interface AgentMessageCompleteEvent {
  type: "agent.message.complete";
  agentId: string;
  content: string;
}

/** Error event */
export interface ErrorEvent {
  type: "error";
  error: string;
}

/** Conversation structure */
export interface Conversation {
  id: string;
  createdAt: number;
  updatedAt: number;
}

/** Chat state interface */
export interface ChatState {
  messages: ChatMessage[];
  currentStreamingMessage: string;
  currentAgentId?: string;
  currentStreamingMessageId?: string;
  currentStreamingTimestamp?: number;
  orchestratorMessages: OrchestratorMessage[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
}

/** Orchestrator message for chain-of-thought */
export interface OrchestratorMessage {
  id: string;
  message: string;
  kind?: string;
  timestamp: number;
}

/** Chat store actions */
export interface ChatActions {
  sendMessage: (message: string) => Promise<void>;
  appendDelta: (delta: string, agentId?: string) => void;
  addMessage: (message: Omit<ChatMessage, "id" | "createdAt">) => void;
  addOrchestratorMessage: (message: string, kind?: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setConversationId: (id: string) => void;
  reset: () => void;
  completeStreaming: () => void;
}

/** Message pattern types */
export type MessagePattern =
  | "steps"
  | "reasoning"
  | "chain_of_thought"
  | "mixed"
  | "plain";

/** Step item structure */
export interface StepItem {
  index: number;
  content: string;
  substeps?: StepItem[];
  completed?: boolean;
  label?: string;
}

/** Reasoning section structure */
export interface ReasoningSection {
  title: string;
  content: string;
  type: "reason" | "explanation" | "rationale";
}

/** Thought node structure */
export interface ThoughtNode {
  id: string;
  content: string;
  timestamp: number;
  type: "fact" | "deduction" | "decision";
}

/** Parsed message structure */
export interface ParsedMessage {
  pattern: MessagePattern;
  data: {
    steps?: StepItem[];
    reasoning?: ReasoningSection[];
    thoughts?: ThoughtNode[];
    plain?: string;
  };
}
