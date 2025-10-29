export interface ChatExecutionResponse {
  execution_id: string;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  created_at: string;
  websocket_url?: string | null;
  message: string;
}

export interface ChatExecutionRequest {
  message: string;
  workflow_id: string;
  conversation_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ApprovalRecord {
  request_id: string;
  details?: Record<string, unknown> | null;
}

export interface ApprovalDecisionPayload {
  decision: "approved" | "rejected" | "modified";
  reason?: string | null;
  modified_code?: string | null;
  modified_params?: Record<string, unknown> | null;
}

export interface HealthResponse {
  status: string;
}
