import { API_BASE_URL } from "@/lib/config";

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
  },
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

      // Process complete SSE messages
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();

          // Handle [DONE] marker
          if (data === "[DONE]") {
            callbacks.onCompleted?.();
            return;
          }

          try {
            const event: {
              type: string;
              delta?: string;
              agent_id?: string;
              error?: string;
              message?: string;
              kind?: string;
            } = JSON.parse(data);

            switch (event.type) {
              case "response.delta":
                if (event.delta) {
                  callbacks.onDelta?.(event.delta, event.agent_id);
                }
                break;

              case "response.completed":
                callbacks.onCompleted?.();
                break;

              case "orchestrator.message":
                if (event.message) {
                  callbacks.onOrchestrator?.(event.message, event.kind);
                }
                break;

              case "agent.message.complete":
                if (event.agent_id && event.content) {
                  callbacks.onAgentComplete?.(event.agent_id, event.content);
                }
                break;

              case "error":
                callbacks.onError?.(event.error || "Unknown error");
                break;

              default:
                // Ignore unknown event types
                break;
            }
          } catch (parseError) {
            // Skip invalid JSON (like keep-alive comments)
            if (data && !data.startsWith(":")) {
              console.warn("Failed to parse SSE event:", data, parseError);
            }
          }
        }
      }
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
