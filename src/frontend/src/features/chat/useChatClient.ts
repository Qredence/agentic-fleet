export type Health = { status: "ok" | "down" };
export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: number;
};
export type Conversation = {
  id: string;
  title: string;
  created_at: number;
  messages: ConversationMessage[];
};
export type ChatResponse = {
  conversation_id: string;
  message: string;
  messages: ConversationMessage[];
};

/**
 * Base API configuration
 * All requests are proxied through Vite to http://localhost:8000
 */
const API_BASE = ""; // Use relative paths - Vite proxy handles /v1/*

/**
 * Health check endpoint
 * GET /v1/system/health
 */
export async function getHealth(): Promise<Health> {
  const r = await fetch(`${API_BASE}/v1/system/health`);
  if (!r.ok) {
    throw new Error(`Health check failed: ${r.status} ${r.statusText}`);
  }
  return r.json();
}

/**
 * Create a new conversation
 * POST /v1/conversations
 */
export async function createConversation(): Promise<Conversation> {
  const r = await fetch(`${API_BASE}/v1/conversations`, { method: "POST" });
  if (!r.ok) {
    throw new Error(
      `Failed to create conversation: ${r.status} ${r.statusText}`,
    );
  }
  return r.json();
}

/**
 * Get conversation by ID
 * GET /v1/conversations/{conversation_id}
 */
export async function getConversation(
  conversationId: string,
): Promise<Conversation> {
  const r = await fetch(`${API_BASE}/v1/conversations/${conversationId}`);
  if (!r.ok) {
    throw new Error(`Failed to get conversation: ${r.status} ${r.statusText}`);
  }
  return r.json();
}

/**
 * Send a chat message (non-streaming)
 * POST /v1/chat
 */
export async function sendChat(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  const r = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!r.ok) {
    const errorText = await r.text().catch(() => "Unknown error");
    throw new Error(
      `Chat request failed: ${r.status} ${r.statusText} - ${errorText}`,
    );
  }
  return r.json();
}

/**
 * SSE Event types from backend
 */
export type SSEEvent = {
  type?: string;
  data?: unknown;
  delta?: string;
};

/**
 * Creates an async iterable that streams Server-Sent Events (SSE) from the backend.
 * Handles the `data: {payload}\n\n` format and `data: [DONE]\n\n` termination.
 *
 * @param url - The SSE endpoint URL
 * @param options - Optional fetch options (method, headers, body, etc.)
 * @returns An async iterable that yields parsed event data strings
 *
 * @example
 * ```ts
 * const stream = streamChatSSE("/v1/chat/stream/123");
 * for await (const chunk of stream) {
 *   console.log(chunk); // Process incremental updates
 * }
 * ```
 */
export async function* streamChatSSE(
  url: string,
  options?: RequestInit,
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      Accept: "text/event-stream",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(
      `SSE request failed: ${response.status} ${response.statusText}`,
    );
  }

  if (!response.body) {
    throw new Error("Response body is null");
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

      // Process complete SSE messages (lines ending with \n\n)
      let newlineIndex: number;
      while ((newlineIndex = buffer.indexOf("\n\n")) !== -1) {
        const message = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 2);

        // Skip empty messages
        if (!message.trim()) {
          continue;
        }

        // Parse SSE format: `data: {payload}` or `data: [DONE]`
        if (message.startsWith("data: ")) {
          const dataContent = message.slice(6).trim(); // Remove "data: " prefix

          // Handle termination signal
          if (dataContent === "[DONE]") {
            return;
          }

          // Parse JSON payload
          try {
            const payload = JSON.parse(dataContent) as SSEEvent;

            // Extract delta text if present
            if (typeof payload === "object" && payload !== null) {
              if ("delta" in payload && typeof payload.delta === "string") {
                yield payload.delta;
              } else if (
                "content" in payload &&
                typeof payload.content === "string"
              ) {
                yield payload.content;
              } else if (typeof payload === "string") {
                yield payload as string;
              } else if ("data" in payload) {
                // Handle nested data structures
                const nestedData = payload.data;
                if (typeof nestedData === "string") {
                  yield nestedData;
                } else if (
                  typeof nestedData === "object" &&
                  nestedData !== null &&
                  "delta" in nestedData &&
                  typeof nestedData.delta === "string"
                ) {
                  yield nestedData.delta;
                }
              }
            } else if (typeof payload === "string") {
              yield payload;
            }
          } catch {
            // If JSON parsing fails, treat the entire content as text
            if (dataContent && dataContent !== "[DONE]") {
              yield dataContent;
            }
          }
        }
      }
    }

    // Process any remaining buffer content
    if (buffer.trim()) {
      // Try to parse remaining buffer as SSE data
      const lines = buffer.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataContent = line.slice(6).trim();
          if (dataContent && dataContent !== "[DONE]") {
            try {
              const payload = JSON.parse(dataContent);
              if (typeof payload === "string") {
                yield payload;
              } else if (
                typeof payload === "object" &&
                payload !== null &&
                "delta" in payload
              ) {
                yield (payload as { delta: string }).delta;
              }
            } catch {
              yield dataContent;
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Sends a chat message and returns an SSE stream for streaming responses.
 * This is the streaming version of sendChat.
 *
 * @param conversationId - The conversation ID
 * @param message - The user message
 * @param stream - Whether to use streaming (default: true)
 * @returns An async iterable that yields incremental response chunks
 */
export async function* sendChatStream(
  conversationId: string,
  message: string,
  stream = true,
): AsyncGenerator<string, void, unknown> {
  if (!stream) {
    // Fallback to non-streaming for compatibility
    const response = await sendChat(conversationId, message);
    yield response.message;
    return;
  }

  const fetchStartTime = performance.now();
  console.log(
    `[NETWORK] Starting fetch request to /v1/chat at ${new Date().toISOString()}`,
  );
  console.log(`[NETWORK] Request body:`, {
    conversation_id: conversationId,
    message: message.substring(0, 50),
    stream: true,
  });

  // Attempt streaming request
  const response = await fetch(`${API_BASE}/v1/chat`, {
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

  const fetchEndTime = performance.now();
  console.log(
    `[NETWORK] Fetch completed. Status: ${response.status} ${response.statusText}`,
  );
  console.log(
    `[NETWORK] Fetch duration: ${(fetchEndTime - fetchStartTime).toFixed(2)}ms`,
  );
  console.log(
    `[NETWORK] Content-Type: ${response.headers.get("content-type")}`,
  );
  console.log(
    `[NETWORK] Response headers:`,
    Object.fromEntries(response.headers.entries()),
  );

  if (!response.ok) {
    console.error(
      `[NETWORK] Request failed: ${response.status} ${response.statusText}`,
    );
    // If streaming request fails, fall back to non-streaming
    try {
      const fallbackResponse = await sendChat(conversationId, message);
      yield fallbackResponse.message;
      return;
    } catch {
      const errorText = await response.text().catch(() => "Unknown error");
      throw new Error(
        `Chat request failed: ${response.status} ${response.statusText} - ${errorText}`,
      );
    }
  }

  // Check if response is streaming
  const contentType = response.headers.get("content-type");
  if (contentType?.includes("text/event-stream") && response.body) {
    console.log(`[NETWORK] Starting to read SSE stream...`);
    const streamStartTime = performance.now();
    // Stream directly from this response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let sseMessageCount = 0;

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log(
            `[NETWORK] Stream reader done. Total SSE messages: ${sseMessageCount}`,
          );
          console.log(
            `[NETWORK] Total stream duration: ${(performance.now() - streamStartTime).toFixed(2)}ms`,
          );
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (lines ending with \n\n)
        let newlineIndex: number;
        while ((newlineIndex = buffer.indexOf("\n\n")) !== -1) {
          sseMessageCount++;
          const message = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 2);

          // Skip empty messages
          if (!message.trim()) {
            continue;
          }

          // Parse SSE format: `data: {payload}` or `data: [DONE]`
          if (message.startsWith("data: ")) {
            const dataContent = message.slice(6).trim();

            // Handle termination signal
            if (dataContent === "[DONE]") {
              console.log(
                `[NETWORK] Received [DONE] signal. Total SSE messages: ${sseMessageCount}`,
              );
              return;
            }

            // Parse JSON payload
            try {
              const payload = JSON.parse(dataContent) as SSEEvent;

              if (sseMessageCount % 10 === 1) {
                console.log(
                  `[NETWORK] SSE message #${sseMessageCount}:`,
                  payload,
                );
              }

              // Extract delta text if present
              if (typeof payload === "object" && payload !== null) {
                if ("delta" in payload && typeof payload.delta === "string") {
                  yield payload.delta;
                } else if (
                  "content" in payload &&
                  typeof payload.content === "string"
                ) {
                  yield payload.content;
                } else if ("data" in payload) {
                  const nestedData = payload.data;
                  if (typeof nestedData === "string") {
                    yield nestedData;
                  } else if (
                    typeof nestedData === "object" &&
                    nestedData !== null &&
                    "delta" in nestedData &&
                    typeof nestedData.delta === "string"
                  ) {
                    yield nestedData.delta;
                  }
                }
              } else if (typeof payload === "string") {
                yield payload;
              }
            } catch (parseError) {
              console.warn(
                `[NETWORK] Failed to parse SSE payload:`,
                dataContent,
                parseError,
              );
              // If JSON parsing fails, treat the entire content as text
              if (dataContent && dataContent !== "[DONE]") {
                yield dataContent;
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
      console.log(`[NETWORK] Stream reader released`);
    }
  } else {
    console.log(`[NETWORK] Response is not SSE, parsing as JSON...`);
    // Fallback: parse JSON response
    const data = (await response.json()) as ChatResponse;
    yield data.message;
  }
}
