export type MessageRole = "user" | "assistant" | "system";

export type AgentRole =
  | "manager"
  | "planner"
  | "executor"
  | "coder"
  | "verifier"
  | "generator"
  | "researcher"
  | "analyst"
  | "user"
  | "assistant";

export type WorkflowEventType =
  | "spawn"
  | "progress"
  | "tool_call"
  | "completion"
  | "error";

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  state: "requested" | "running" | "output-available" | "output-error";
  output?: unknown;
  errorText?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  actor?: string;
  agentRole?: AgentRole;
  agentType?: AgentRole;
  toolCalls?: ToolCall[];
  metadata?: Record<string, unknown>;
}

export type ChatStatus = "ready" | "submitted" | "streaming" | "error";
export type ConnectionStatus = "connected" | "disconnected" | "error";

export interface QueueStatus {
  phase: "waiting" | "running" | "finished";
  inflight: number;
  queued: number;
  maxParallel: number;
}

export interface PlanStep {
  id: string;
  title: string;
  status: "pending" | "active" | "completed" | "blocked";
  assignee?: AgentRole;
  summary?: string;
}

export interface Plan {
  id: string;
  title: string;
  createdAt: string;
  updatedAt?: string;
  steps: PlanStep[];
}

export interface PendingApproval {
  id: string;
  requestId: string;
  operation?: string;
  description?: string;
  details?: Record<string, unknown>;
  timestamp: number;
  riskLevel?: "low" | "medium" | "high";
}

export type ApprovalActionState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success" }
  | { status: "error"; error: string };

export type ApprovalResponsePayload =
  | { type: "approve"; reason?: string }
  | { type: "reject"; reason: string }
  | {
      type: "modify";
      reason?: string;
      modifiedCode?: string;
      modifiedParams?: Record<string, unknown>;
    };

export type AnySSEEvent = {
  type: string;
  [key: string]: unknown;
};
