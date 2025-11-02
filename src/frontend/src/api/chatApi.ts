import axios, { AxiosError } from "axios";

// API Types
export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  agentsInvolved: string[];
  metadata: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  agentName?: string;
  attachments?: Attachment[];
  metadata?: Record<string, any>;
  streaming?: boolean;
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
}

export interface VoiceInputData {
  audioBlob: Blob;
  format: string;
  duration: number;
}

export interface SearchRequest {
  query: string;
  filters: {
    agentTypes?: string[];
    dateRange?: { start: string; end: string };
    hasAttachments?: boolean;
    isBookmarked?: boolean;
  };
  limit?: number;
  offset?: number;
}

export interface SearchResponse {
  conversations: ChatConversation[];
  totalCount: number;
  hasMore: boolean;
}

export interface StreamingControl {
  action: "pause" | "resume" | "stop";
  messageId: string;
}

export interface FileUploadResponse {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
}

export interface SpeechToTextResponse {
  text: string;
  confidence: number;
  alternatives?: Array<{
    text: string;
    confidence: number;
  }>;
}

export interface PerformanceMetrics {
  conversationId: string;
  messageId: string;
  metrics: {
    responseTime: number;
    streamingLatency: number;
    chunkCount: number;
    agentProcessingTime: number;
    totalTokens: number;
  };
}

// API Client
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ChatApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any,
  ) {
    super(message);
    this.name = "ChatApiError";
  }
}

class ChatApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ChatApiError(
          errorData.message || `HTTP ${response.status}`,
          response.status,
          errorData.code,
          errorData.details,
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ChatApiError) {
        throw error;
      }

      if (error instanceof Error) {
        throw new ChatApiError(`Network error: ${error.message}`);
      }

      throw new ChatApiError("Unknown network error");
    }
  }

  // Conversation Management
  async createConversation(title?: string): Promise<ChatConversation> {
    return this.request<ChatConversation>("/v1/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  }

  async getConversation(id: string): Promise<ChatConversation> {
    return this.request<ChatConversation>(`/v1/conversations/${id}`);
  }

  async updateConversation(
    id: string,
    updates: Partial<ChatConversation>,
  ): Promise<ChatConversation> {
    return this.request<ChatConversation>(`/v1/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request<void>(`/v1/conversations/${id}`, {
      method: "DELETE",
    });
  }

  async listConversations(limit = 50, offset = 0): Promise<ChatConversation[]> {
    return this.request<ChatConversation[]>(
      `/v1/conversations?limit=${limit}&offset=${offset}`,
    );
  }

  // Message Management
  async sendMessage(
    conversationId: string,
    message: {
      content: string;
      attachments?: string[];
      tools?: string[];
      voiceData?: VoiceInputData;
    },
    useStreaming = true,
  ): Promise<ChatMessage> {
    return this.request<ChatMessage>(
      `/v1/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({
          ...message,
          streaming: useStreaming,
        }),
      },
    );
  }

  async getMessage(
    conversationId: string,
    messageId: string,
  ): Promise<ChatMessage> {
    return this.request<ChatMessage>(
      `/v1/conversations/${conversationId}/messages/${messageId}`,
    );
  }

  async updateMessage(
    conversationId: string,
    messageId: string,
    updates: Partial<ChatMessage>,
  ): Promise<ChatMessage> {
    return this.request<ChatMessage>(
      `/v1/conversations/${conversationId}/messages/${messageId}`,
      {
        method: "PATCH",
        body: JSON.stringify(updates),
      },
    );
  }

  async deleteMessage(
    conversationId: string,
    messageId: string,
  ): Promise<void> {
    await this.request<void>(
      `/v1/conversations/${conversationId}/messages/${messageId}`,
      {
        method: "DELETE",
      },
    );
  }

  // Streaming
  async *streamMessage(
    conversationId: string,
    message: {
      content: string;
      attachments?: string[];
      tools?: string[];
      voiceData?: VoiceInputData;
    },
  ): AsyncGenerator<string, void, unknown> {
    const response = await fetch(
      `${this.baseURL}/v1/conversations/${conversationId}/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(message),
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ChatApiError(
        errorData.message || `HTTP ${response.status}`,
        response.status,
        errorData.code,
        errorData.details,
      );
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new ChatApiError("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                yield parsed.content;
              }
            } catch (e) {
              console.warn("Failed to parse SSE data:", data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async controlStreaming(
    conversationId: string,
    control: StreamingControl,
  ): Promise<void> {
    await this.request<void>(
      `/v1/conversations/${conversationId}/streaming/control`,
      {
        method: "POST",
        body: JSON.stringify(control),
      },
    );
  }

  // Search and Filtering
  async searchConversations(request: SearchRequest): Promise<SearchResponse> {
    const params = new URLSearchParams();
    params.set("q", request.query);

    if (request.filters.agentTypes) {
      params.set("agentTypes", request.filters.agentTypes.join(","));
    }
    if (request.filters.dateRange) {
      params.set("dateStart", request.filters.dateRange.start);
      params.set("dateEnd", request.filters.dateRange.end);
    }
    if (request.filters.hasAttachments) {
      params.set("hasAttachments", "true");
    }
    if (request.filters.isBookmarked) {
      params.set("isBookmarked", "true");
    }
    if (request.limit) {
      params.set("limit", request.limit.toString());
    }
    if (request.offset) {
      params.set("offset", request.offset.toString());
    }

    return this.request<SearchResponse>(`/v1/conversations/search?${params}`);
  }

  // File Management
  async uploadFile(
    file: File,
    conversationId?: string,
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (conversationId) {
      formData.append("conversationId", conversationId);
    }

    const response = await fetch(`${this.baseURL}/v1/files/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ChatApiError(
        errorData.message || `HTTP ${response.status}`,
        response.status,
        errorData.code,
        errorData.details,
      );
    }

    return response.json();
  }

  async deleteFile(fileId: string): Promise<void> {
    await this.request<void>(`/v1/files/${fileId}`, {
      method: "DELETE",
    });
  }

  // Voice Input
  async speechToText(audioData: VoiceInputData): Promise<SpeechToTextResponse> {
    const formData = new FormData();
    formData.append("audio", audioData.audioBlob, `audio.${audioData.format}`);
    formData.append("format", audioData.format);
    formData.append("duration", audioData.duration.toString());

    const response = await fetch(`${this.baseURL}/v1/speech-to-text`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ChatApiError(
        errorData.message || `HTTP ${response.status}`,
        response.status,
        errorData.code,
        errorData.details,
      );
    }

    return response.json();
  }

  // Performance Monitoring
  async reportMetrics(metrics: PerformanceMetrics): Promise<void> {
    await this.request<void>(`/v1/metrics`, {
      method: "POST",
      body: JSON.stringify(metrics),
    });
  }

  // Health Check
  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
    version?: string;
  }> {
    return this.request<{
      status: string;
      timestamp: string;
      version?: string;
    }>("/health");
  }

  // WebSocket Connection (for real-time features)
  connectWebSocket(conversationId: string): WebSocket {
    const wsUrl = `${this.baseURL.replace("http", "ws")}/v1/conversations/${conversationId}/ws`;
    return new WebSocket(wsUrl);
  }
}

// Export singleton instance
export const chatApi = new ChatApiClient();

// Export types
export type { ChatApiError };
export default chatApi;
