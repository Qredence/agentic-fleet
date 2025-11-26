import type { Conversation, ChatRequest } from "./types";

const API_PREFIX = import.meta.env.VITE_API_PREFIX || "/api";

export const api = {
  /**
   * Create a new conversation
   */
  createConversation: async (title?: string): Promise<Conversation> => {
    const response = await fetch(`${API_PREFIX}/conversations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error("Failed to create conversation");
    }

    return response.json();
  },

  /**
   * List all conversations
   */
  listConversations: async (): Promise<Conversation[]> => {
    const response = await fetch(`${API_PREFIX}/conversations`);

    if (!response.ok) {
      throw new Error("Failed to list conversations");
    }

    const data = await response.json();
    // Backend returns { items: [...] } format
    return data.items || data;
  },

  /**
   * Get a specific conversation by ID
   */
  getConversation: async (id: number | string): Promise<Conversation> => {
    const response = await fetch(`${API_PREFIX}/conversations/${id}`);

    if (!response.ok) {
      throw new Error("Failed to get conversation");
    }

    return response.json();
  },

  /**
   * Send a message to the chat endpoint (supports streaming)
   */
  sendMessage: async (
    request: ChatRequest,
    signal?: AbortSignal,
  ): Promise<Response> => {
    const response = await fetch(`${API_PREFIX}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      throw new Error("Failed to send message");
    }

    return response;
  },

  /**
   * Health check endpoint
   */
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await fetch(`${API_PREFIX}/health`);

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    return response.json();
  },
};
