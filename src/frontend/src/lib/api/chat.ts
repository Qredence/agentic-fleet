import { API_BASE_URL } from "@/lib/config";
import { processBuffer, type SSEEvent } from "@/lib/streaming/sseParser";

/** Create a new conversation */
export async function createConversation(): Promise<{
  id: string;
  title: string;
  created_at: number;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: number;
  }>;
}> {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create conversation: ${error}`);
  }

  return response.json();
}

/** Get conversation by ID with message history */
export async function getConversation(conversationId: string): Promise<{
  id: string;
  title: string;
  created_at: number;
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    created_at: number;
    reasoning?: string | null;
  }>;
}> {
  const response = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Conversation not found: ${conversationId}`);
    }
    const error = await response.text();
    throw new Error(`Failed to get conversation: ${error}`);
  }

  return response.json();
}

/** List all conversations */
export async function listConversations(): Promise<{
  items: Array<{
    id: string;
    title: string;
    created_at: number;
    messages: Array<{
      id: string;
      role: "user" | "assistant" | "system";
      content: string;
      created_at: number;
      reasoning?: string | null;
    }>;
  }>;
}> {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to list conversations: ${error}`);
  }

  return response.json();
}

/** SSE Event callback types */
export type SSEDeltaCallback = (delta: string, agentId?: string) => void;
export type SSECompletedCallback = () => void;
export type SSEOrchestratorCallback = (message: string, kind?: string) => void;
export type SSEErrorCallback = (error: string) => void;

/** Stream chat response using Server-Sent Events */
export async function streamChatResponse(
  conversationId: string,
  message: string,
  callbacks: {
    onDelta?: SSEDeltaCallback;
    onCompleted?: SSECompletedCallback;
    onOrchestrator?: SSEOrchestratorCallback;
    onError?: SSEErrorCallback;
    onAgentComplete?: (agentId: string, content: string) => void;
    onReasoningDelta?: (reasoning: string) => void;
    onReasoningCompleted?: (reasoning: string) => void;
  },
  options?: { signal?: AbortSignal },
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      stream: true,
    }),
    signal: options?.signal,
  });

  if (!response.ok) {
    const error = await response.text();
    callbacks.onError?.(`HTTP error: ${error}`);
    return;
  }

  if (!response.body) {
    callbacks.onError?.("No response body");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      buffer = processBuffer(buffer, (evt: SSEEvent) => {
        if (evt.type === "__done__") {
          callbacks.onCompleted?.();
          return;
        }

        switch (evt.type) {
          case "response.delta": {
            const agentId = evt.agentId ?? evt.agent_id;
            callbacks.onDelta?.(evt.delta, agentId);
            break;
          }
          case "response.completed":
            callbacks.onCompleted?.();
            break;
          case "orchestrator.message":
            callbacks.onOrchestrator?.(evt.message, evt.kind);
            break;
          case "agent.message.complete": {
            const agentId = evt.agentId ?? evt.agent_id;
            if (agentId) {
              callbacks.onAgentComplete?.(agentId, evt.content);
            }
            break;
          }
          case "reasoning.delta":
            callbacks.onReasoningDelta?.(evt.reasoning);
            break;
          case "reasoning.completed":
            callbacks.onReasoningCompleted?.(evt.reasoning || "");
            break;
          case "error":
            callbacks.onError?.(evt.error || "Unknown error");
            break;
          default:
            // Handle unknown event types gracefully
            break;
        }
      });
    }

    // Final completion if stream ends without [DONE]
    callbacks.onCompleted?.();
  } catch (error) {
    callbacks.onError?.(
      error instanceof Error ? error.message : "Unknown streaming error",
    );
  } finally {
    reader.releaseLock();
  }
}

/** Send a chat message (non-streaming) */
export async function sendChatMessage(
  conversationId: string,
  message: string,
): Promise<{
  conversation_id: string;
  message: string;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: number;
  }>;
}> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      stream: false,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to send message: ${error}`);
  }

  return response.json();
}
