export interface Message {
  id?: number | string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface Conversation {
  id: number | string;
  title: string;
  created_at: string;
  updated_at?: string;
  messages?: Message[];
}

export interface CreateConversationRequest {
  title?: string;
}

export interface ChatRequest {
  conversation_id: number | string;
  message: string;
  stream?: boolean;
}

export interface ChatResponse {
  conversation_id: number | string;
  message: string;
  messages: Message[];
}

export interface ThoughtItem {
  type: "text" | "file";
  text: string;
  file?: {
    name: string;
    icon?: string;
    color?: string;
  };
}

export interface Thought {
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "success" | "failed";
  items?: ThoughtItem[];
}

export interface StreamEvent {
  type:
    | "orchestrator.message"
    | "orchestrator.thought"
    | "response.delta"
    | "response.completed"
    | "error";
  message?: string;
  delta?: string;
  agent_id?: string;
  kind?: "thought" | "status";
  error?: string;
  thought?: Thought;
}
