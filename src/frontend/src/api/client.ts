import type {
  Conversation,
  WorkflowSession,
  AgentInfo,
  Message,
  IntentRequest,
  IntentResponse,
  EntityRequest,
  EntityResponse,
} from "./types";

const API_PREFIX = "/api/v1";

export const api = {
  // ... existing methods ...

  async classifyIntent(request: IntentRequest): Promise<IntentResponse> {
    const response = await fetch(`${API_PREFIX}/classify_intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error("Failed to classify intent");
    return response.json();
  },

  async extractEntities(request: EntityRequest): Promise<EntityResponse> {
    const response = await fetch(`${API_PREFIX}/extract_entities`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error("Failed to extract entities");
    return response.json();
  },

  async createConversation(title: string = "New Chat"): Promise<Conversation> {
    const response = await fetch(`${API_PREFIX}/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) throw new Error("Failed to create conversation");
    return response.json();
  },

  async getConversation(id: string): Promise<Conversation> {
    const response = await fetch(`${API_PREFIX}/conversations/${id}`);
    if (!response.ok) throw new Error("Failed to get conversation");
    return response.json();
  },

  async listConversations(): Promise<Conversation[]> {
    const response = await fetch(`${API_PREFIX}/conversations`);
    if (!response.ok) throw new Error("Failed to list conversations");
    return response.json();
  },

  async loadConversationMessages(id: string): Promise<Message[]> {
    const conversation = await this.getConversation(id);
    return conversation.messages || [];
  },

  async listSessions(): Promise<WorkflowSession[]> {
    const response = await fetch(`${API_PREFIX}/sessions`);
    if (!response.ok) throw new Error("Failed to list sessions");
    return response.json();
  },

  async getSession(id: string): Promise<WorkflowSession> {
    const response = await fetch(`${API_PREFIX}/sessions/${id}`);
    if (!response.ok) throw new Error("Failed to get session");
    return response.json();
  },

  async cancelSession(id: string): Promise<void> {
    const response = await fetch(`${API_PREFIX}/sessions/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to cancel session");
  },

  async listAgents(): Promise<AgentInfo[]> {
    const response = await fetch(`${API_PREFIX}/agents`);
    if (!response.ok) throw new Error("Failed to list agents");
    return response.json();
  },
};
