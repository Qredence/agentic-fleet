import { useCallback, useEffect, useRef, useState } from "react";
import {
  streamChatResponse,
  type SSEDeltaCallback,
  type SSECompletedCallback,
  type SSEOrchestratorCallback,
  type SSEErrorCallback,
} from "@/lib/api/chat";

/**
 * Options for useSSEStream hook callbacks.
 * These mirror the callbacks used by streamChatResponse and are forwarded.
 */
export interface UseSSEStreamOptions {
  onDelta?: SSEDeltaCallback;
  onAgentComplete?: (agentId: string, content: string) => void;
  onCompleted?: SSECompletedCallback;
  onError?: SSEErrorCallback;
  onReasoningCompleted?: (reasoning: string) => void;
  onOrchestrator?: SSEOrchestratorCallback;
}

/**
 * Custom hook to manage SSE chat streaming lifecycle with AbortController.
 *
 * Provides:
 * - isStreaming: boolean state indicating active stream
 * - error: last error message (if any)
 * - stream(conversationId, message): starts streaming and forwards events
 * - cancel(): aborts active fetch/stream gracefully
 */
export function useSSEStream(options: UseSSEStreamOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stream = useCallback(
    async (conversationId: string, message: string) => {
      // Prevent starting multiple streams
      if (isStreaming) return;

      setIsStreaming(true);
      setError(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        await streamChatResponse(
          conversationId,
          message,
          {
            onDelta: options.onDelta,
            onAgentComplete: options.onAgentComplete,
            onCompleted: options.onCompleted,
            onOrchestrator: options.onOrchestrator,
            onError: (err) => {
              // If aborted, do not surface as error
              if (err === "AbortError") return;
              setError(err);
              options.onError?.(err);
            },
            onReasoningCompleted: options.onReasoningCompleted,
          },
          { signal: controller.signal },
        );
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Unknown streaming error";
        // If aborted, treat as graceful stop
        if ((err as any)?.name === "AbortError") {
          options.onCompleted?.();
        } else {
          setError(msg);
          options.onError?.(msg);
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [
      isStreaming,
      options.onDelta,
      options.onAgentComplete,
      options.onCompleted,
      options.onOrchestrator,
      options.onError,
      options.onReasoningCompleted,
    ],
  );

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  // Cleanup effect to abort in-flight stream on component unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  return { stream, cancel, isStreaming, error };
}
