/**
 * Custom hook for handling streaming chat messages
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { sendMessageStreaming } from "../lib/api/chatApi";
import { parseSSEStream, type StreamEvent } from "../lib/streamParser";

export interface UseStreamingChatOptions {
  onMessageComplete?: (content: string) => void;
  onReasoningDelta?: (reasoning: string) => void;
  onDelta?: (content: string, agentId?: string) => void;
  onError?: (error: Error) => void;
}

export interface UseStreamingChatReturn {
  isStreaming: boolean;
  streamingContent: string;
  orchestratorThought: string;
  currentAgentId?: string;
  sendMessage: (conversationId: string, message: string) => Promise<void>;
  cancelStream: () => void;
}

export function useStreamingChat({
  onMessageComplete,
  onReasoningDelta,
  onDelta,
  onError,
}: UseStreamingChatOptions): UseStreamingChatReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [orchestratorThought, setOrchestratorThought] = useState("");
  const [currentAgentId, setCurrentAgentId] = useState<string | undefined>();
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setStreamingContent("");
    setOrchestratorThought("");
    setCurrentAgentId(undefined);
  }, []);

  const sendMessage = useCallback(
    async (conversationId: string, message: string) => {
      // Reset state
      setStreamingContent("");
      setOrchestratorThought("");
      setCurrentAgentId(undefined);
      setIsStreaming(true);
      let activeAgentId: string | undefined;

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      try {
        // Start streaming
        const stream = await sendMessageStreaming(
          {
            conversation_id: conversationId,
            message,
            stream: true,
          },
          { signal: abortControllerRef.current.signal },
        );

        // Accumulate content
        let fullContent = "";
        let reasoningContent = "";

        // Parse stream
        await parseSSEStream(
          stream,
          (event: StreamEvent) => {
            switch (event.type) {
              case "orchestrator.message":
                setOrchestratorThought(event.message);
                break;

              case "response.delta":
                fullContent += event.delta;
                setStreamingContent(fullContent);
                if (event.agent_id) {
                  activeAgentId = event.agent_id;
                  setCurrentAgentId(event.agent_id);
                }
                onDelta?.(fullContent, activeAgentId);
                break;

              case "response.completed":
              case "agent.message.complete":
                setIsStreaming(false);
                setOrchestratorThought("");
                onDelta?.(fullContent, activeAgentId);
                if (onMessageComplete) {
                  const content =
                    event.type === "agent.message.complete" && event.content
                      ? event.content
                      : fullContent;
                  onMessageComplete(content);
                }
                break;

              case "reasoning.delta":
                reasoningContent += event.reasoning;
                onReasoningDelta?.(reasoningContent);
                break;

              case "reasoning.completed":
                reasoningContent = event.reasoning || reasoningContent;
                onReasoningDelta?.(reasoningContent);
                break;

              case "error":
                setIsStreaming(false);
                if (onError) {
                  onError(new Error(event.error));
                }
                break;

              case "done":
                setIsStreaming(false);
                setOrchestratorThought("");
                break;
            }
          },
          (error) => {
            setIsStreaming(false);
            setOrchestratorThought("");
            if (onError) {
              onError(error);
            }
          },
        );
      } catch (error) {
        setIsStreaming(false);
        setOrchestratorThought("");
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
      }
    },
    [onMessageComplete, onReasoningDelta, onDelta, onError, currentAgentId],
  );

  // Clean up on unmount
  useEffect(() => cancelStream, [cancelStream]);

  return {
    isStreaming,
    streamingContent,
    orchestratorThought,
    currentAgentId,
    sendMessage,
    cancelStream,
  };
}
