/**
 * useMessageState Hook
 *
 * Manages message accumulation and streaming state
 * Now includes batched delta updates for better performance
 */

import { useState, useCallback, useRef } from "react";

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  actor?: string;
  isNew?: boolean;
  toolCalls?: ToolCall[];
}

export interface UseMessageStateReturn {
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  isStreaming: () => boolean;
  startStreamingMessage: (
    itemId: string,
    delta: string,
    actor?: string,
  ) => void;
  appendDelta: (delta: string) => void;
  finishStreaming: () => void;
  resetStreaming: () => void;
}

export function useMessageState(): UseMessageStateReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(
    null,
  );
  const deltaBufferRef = useRef<string>("");
  const rafIdRef = useRef<number | null>(null);

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentStreamingId(null);
    deltaBufferRef.current = "";
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }, []);

  const isStreaming = useCallback(() => {
    return currentStreamingId !== null;
  }, [currentStreamingId]);

  const startStreamingMessage = useCallback(
    (itemId: string, delta: string, actor?: string) => {
      const newMessage: Message = {
        id: itemId,
        role: "assistant",
        content: delta,
        actor,
        isNew: true,
      };
      setMessages((prev) => [...prev, newMessage]);
      setCurrentStreamingId(itemId);
      deltaBufferRef.current = ""; // Clear buffer for new message
    },
    [],
  );

  const flushDeltaBuffer = useCallback(() => {
    if (deltaBufferRef.current === "") return;

    const deltaToAppend = deltaBufferRef.current;
    deltaBufferRef.current = "";

    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (!lastMessage) return prev;

      return [
        ...prev.slice(0, -1),
        {
          ...lastMessage,
          content: lastMessage.content + deltaToAppend,
        },
      ];
    });

    rafIdRef.current = null;
  }, []);

  const appendDelta = useCallback(
    (delta: string) => {
      deltaBufferRef.current += delta;

      // Batch updates using requestAnimationFrame (throttle to ~60fps)
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushDeltaBuffer);
      }
    },
    [flushDeltaBuffer],
  );

  const finishStreaming = useCallback(() => {
    // Flush any remaining buffered deltas
    if (deltaBufferRef.current !== "") {
      flushDeltaBuffer();
    }
    setCurrentStreamingId(null);
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }, [flushDeltaBuffer]);

  const resetStreaming = useCallback(() => {
    deltaBufferRef.current = "";
    setCurrentStreamingId(null);
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }, []);

  return {
    messages,
    setMessages,
    addMessage,
    clearMessages,
    isStreaming,
    startStreamingMessage,
    appendDelta,
    finishStreaming,
    resetStreaming,
  };
}
