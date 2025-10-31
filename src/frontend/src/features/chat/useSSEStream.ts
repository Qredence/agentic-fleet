import { useCallback, useRef } from "react";

export type SSEMessage = {
  type: "delta" | "done";
  delta?: string;
};

export type SSEEventHandler = {
  onMessage: (message: SSEMessage) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
};

/**
 * Hook for managing Server-Sent Events (SSE) connection for chat streaming.
 *
 * @returns An object with connect and disconnect methods for SSE stream management
 */
export function useSSEStream() {
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(
    (conversationId: string, message: string, handlers: SSEEventHandler) => {
      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Create FormData for POST request via EventSource
      // Note: EventSource API only supports GET by default
      // We'll use fetch with ReadableStream instead
      const controller = new AbortController();

      fetch("/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ conversation_id: conversationId, message }),
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const reader = response.body?.getReader();
          const decoder = new TextDecoder();

          if (!reader) {
            throw new Error("Response body is not readable");
          }

          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              handlers.onComplete();
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6);
                try {
                  const parsed = JSON.parse(data) as SSEMessage;
                  handlers.onMessage(parsed);

                  if (parsed.type === "done") {
                    handlers.onComplete();
                    reader.cancel();
                    return;
                  }
                } catch (e) {
                  console.error("Failed to parse SSE message:", e);
                }
              }
            }
          }
        })
        .catch((error) => {
          if (error.name !== "AbortError") {
            handlers.onError(error);
          }
        });

      return () => controller.abort();
    },
    [],
  );

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  return { connect, disconnect };
}
