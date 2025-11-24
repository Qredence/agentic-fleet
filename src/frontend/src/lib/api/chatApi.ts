/**
 * Chat API Client
 * Handles all communication with the FastAPI backend chat endpoints
 */

import { API_BASE_URL } from "../config";

type FetchOptions = RequestInit & { signal?: AbortSignal };

const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
};

async function fetchJson<T>(path: string, init: FetchOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...DEFAULT_HEADERS,
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(
      `Request failed ${response.status}: ${response.statusText}${
        errorText ? ` - ${errorText}` : ""
      }`,
    );
  }

  // Some endpoints may legitimately return no body (e.g., DELETE)
  if (response.status === 204) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return undefined as any;
  }

  return response.json() as Promise<T>;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: number;
  reasoning?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: number;
  messages: Message[];
}

export interface CreateConversationRequest {
  title?: string;
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
  stream?: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  messages: Message[];
}

/**
 * Create a new conversation
 */
export async function createConversation(
  request: CreateConversationRequest = {},
  options: FetchOptions = {},
): Promise<Conversation> {
  return fetchJson<Conversation>("/conversations", {
    method: "POST",
    body: JSON.stringify(request),
    ...options,
  });
}

/**
 * List all conversations
 */
export async function listConversations(): Promise<Conversation[]> {
  const data = await fetchJson<{ items?: Conversation[] }>("/conversations");
  return data.items || [];
}

/**
 * Get a specific conversation by ID
 */
export async function getConversation(
  conversationId: string,
): Promise<Conversation> {
  return fetchJson<Conversation>(`/conversations/${conversationId}`);
}

/**
 * Send a message (non-streaming)
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  return fetchJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ ...request, stream: false }),
  });
}

/**
 * Send a message with streaming response
 * Returns a ReadableStream that yields SSE events
 */
export async function sendMessageStreaming(
  request: ChatRequest,
  options: FetchOptions = {},
): Promise<ReadableStream<Uint8Array>> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({ ...request, stream: true }),
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(
      `Failed to send message: ${response.statusText}${
        errorText ? ` - ${errorText}` : ""
      }`,
    );
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  return response.body;
}
