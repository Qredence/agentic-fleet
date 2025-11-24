/**
 * Server-Sent Events (SSE) Stream Parser
 * Robustly parses SSE events from the chat API streaming response using eventsource-parser.
 */

import {
  createParser,
  type ParsedEvent,
  type ReconnectInterval,
} from "eventsource-parser";

export type StreamEventType =
  | "orchestrator.message"
  | "response.delta"
  | "response.completed"
  | "agent.message.complete"
  | "reasoning.delta"
  | "reasoning.completed"
  | "error"
  | "done";

export interface OrchestratorMessage {
  type: "orchestrator.message";
  message: string;
  kind?: "thought" | "action" | "observation" | string;
  agent_id?: string;
}

export interface ResponseDelta {
  type: "response.delta";
  delta: string;
  agent_id?: string;
}

export interface ResponseCompleted {
  type: "response.completed";
  agent_id?: string;
}

export interface AgentMessageCompleted {
  type: "agent.message.complete";
  content: string;
  agent_id?: string;
}

export interface ReasoningDelta {
  type: "reasoning.delta";
  reasoning: string;
}

export interface ReasoningCompleted {
  type: "reasoning.completed";
  reasoning: string;
}

export interface StreamError {
  type: "error";
  error: string;
}

export interface StreamDone {
  type: "done";
}

export type StreamEvent =
  | OrchestratorMessage
  | ResponseDelta
  | ResponseCompleted
  | AgentMessageCompleted
  | ReasoningDelta
  | ReasoningCompleted
  | StreamError
  | StreamDone;

function normalizeEvent(
  evt: ParsedEvent | ReconnectInterval,
): StreamEvent | null {
  if (evt.type === "reconnect-interval") return null;
  // event
  if (evt.data === "[DONE]" || evt.event === "done") {
    return { type: "done" };
  }

  let payload: Record<string, unknown> = {};
  try {
    payload = evt.data ? JSON.parse(evt.data) : {};
  } catch {
    // Non-JSON payloads are ignored to avoid throwing the stream
    return null;
  }

  const typeFromEvent =
    (evt.event as StreamEventType | undefined) ||
    (payload.type as StreamEventType | undefined);
  if (!typeFromEvent) {
    return null;
  }

  return {
    type: typeFromEvent,
    ...payload,
  } as StreamEvent;
}

/**
 * Parse SSE stream and invoke callback for each event
 */
export async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: Error) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  const parser = createParser({
    onEvent: (event) => {
      const normalized = normalizeEvent(event);
      if (normalized) {
        onEvent(normalized);
      }
    },
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error(String(error)));
  } finally {
    reader.releaseLock();
  }
}

/**
 * Create an async iterator from an SSE stream
 */
export async function* streamToAsyncIterator(
  stream: ReadableStream<Uint8Array>,
): AsyncIterableIterator<StreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  const queue: StreamEvent[] = [];
  const parser = createParser({
    onEvent: (event) => {
      const normalized = normalizeEvent(event);
      if (!normalized) return;
      queue.push(normalized);
    },
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));

      while (queue.length) {
        yield queue.shift() as StreamEvent;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
