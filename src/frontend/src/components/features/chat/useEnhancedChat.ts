import { useCallback, useEffect, useRef, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { chatApi } from "@/api/chatApi";
import { performanceMonitor, usePerformanceMonitor } from "@/utils/performance";
import type { ChatMessage } from "./useChatController";
import type { ProcessedFile } from "@/utils/fileHandling";

interface UseEnhancedChatOptions {
  autoSaveDrafts?: boolean;
  enablePerformanceMonitoring?: boolean;
  onError?: (error: Error) => void;
  onSuccess?: (message: ChatMessage) => void;
}

interface EnhancedChatState {
  isLoading: boolean;
  isStreaming: boolean;
  streamingProgress: {
    messageId: string | null;
    agentName: string | null;
    progress: number;
    eta: number | null;
  };
  error: string | null;
  canPauseStream: boolean;
  canResumeStream: boolean;
}

export const useEnhancedChat = (options: UseEnhancedChatOptions = {}) => {
  const {
    autoSaveDrafts = true,
    enablePerformanceMonitoring = true,
    onError,
    onSuccess,
  } = options;

  // Store integration
  const {
    currentConversationId,
    messages,
    setCurrentConversation,
    addMessage,
    updateMessage,
    getMessages,
    streaming,
    startStreaming,
    updateStreaming,
    stopStreaming,
    pauseStreaming,
    resumeStreaming,
    input,
    updateInput,
    saveInputDraft,
    clearInput,
    recordMetric,
  } = useChatStore();

  // Performance monitoring
  const perf = usePerformanceMonitor();

  // State management
  const [state, setState] = useState<EnhancedChatState>({
    isLoading: false,
    isStreaming: streaming.isStreaming,
    streamingProgress: {
      messageId: streaming.currentMessageId,
      agentName: streaming.agentName,
      progress: 0,
      eta: streaming.estimatedCompletion
        ? Math.max(0, (streaming.estimatedCompletion - Date.now()) / 1000)
        : null,
    },
    error: null,
    canPauseStream: streaming.isStreaming,
    canResumeStream:
      !streaming.isStreaming && streaming.currentMessageId !== null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  // Update streaming state when store changes
  useEffect(() => {
    setState((prev) => ({
      ...prev,
      isStreaming: streaming.isStreaming,
      streamingProgress: {
        messageId: streaming.currentMessageId,
        agentName: streaming.agentName,
        progress:
          streaming.chunkCount > 0
            ? Math.min(100, (streaming.chunkCount / 50) * 100)
            : 0,
        eta: streaming.estimatedCompletion
          ? Math.max(0, (streaming.estimatedCompletion - Date.now()) / 1000)
          : null,
      },
      canPauseStream: streaming.isStreaming,
      canResumeStream:
        !streaming.isStreaming && streaming.currentMessageId !== null,
    }));
  }, [streaming]);

  // Auto-save drafts
  useEffect(() => {
    if (!autoSaveDrafts || !currentConversationId) return;

    const saveDraft = () => {
      if (input.content.trim()) {
        saveInputDraft();
      }
    };

    const intervalId = setInterval(saveDraft, 5000);
    return () => clearInterval(intervalId);
  }, [autoSaveDrafts, currentConversationId, input.content, saveInputDraft]);

  // Initialize conversation
  const initializeConversation = useCallback(
    async (conversationId?: string) => {
      try {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        let conv;
        if (conversationId) {
          conv = await chatApi.getConversation(conversationId);
          setCurrentConversation(conversationId);
        } else {
          conv = await chatApi.createConversation();
          setCurrentConversation(conv.id);
        }

        // Load messages into store
        conv.messages.forEach((msg) => {
          addMessage(conv.id, {
            id: msg.id,
            role: msg.role,
            content: msg.content,
            streaming: false,
          });
        });

        setState((prev) => ({ ...prev, isLoading: false }));
        return conv;
      } catch (error) {
        const err =
          error instanceof Error
            ? error
            : new Error("Failed to initialize conversation");
        setState((prev) => ({ ...prev, isLoading: false, error: err.message }));
        onError?.(err);
        throw err;
      }
    },
    [setCurrentConversation, addMessage, onError],
  );

  // Send message with enhanced features
  const sendMessage = useCallback(
    async (
      content: string,
      attachments: ProcessedFile[] = [],
      tools: string[] = [],
      voiceData?: any,
    ) => {
      if (!currentConversationId) {
        await initializeConversation();
      }

      const conversationId =
        currentConversationId || (await initializeConversation()).id;

      try {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        const startTracking = enablePerformanceMonitoring
          ? perf.startInteraction("send-message")
          : () => {};

        // Add user message immediately
        const userMessage: ChatMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content,
          streaming: false,
        };

        addMessage(conversationId, userMessage);

        // Start performance monitoring
        if (enablePerformanceMonitoring) {
          perf.startStreamMonitoring(userMessage.id, conversationId);
        }

        // Prepare message data
        const messageData: any = {
          content,
          tools: tools.length > 0 ? tools : undefined,
          voiceData,
        };

        // Handle file uploads
        if (attachments.length > 0) {
          const uploadPromises = attachments.map(async (file) => {
            const uploadResult = await chatApi.uploadFile(
              file.file,
              conversationId,
            );
            return uploadResult.id;
          });

          const attachmentIds = await Promise.all(uploadPromises);
          messageData.attachments = attachmentIds;
        }

        // Create assistant message placeholder
        const assistantMessageId = `assistant-${Date.now()}`;
        const assistantMessage: ChatMessage = {
          id: assistantMessageId,
          role: "assistant",
          content: "",
          streaming: true,
        };

        addMessage(conversationId, assistantMessage);
        startStreaming(assistantMessageId, "Assistant");

        // Cancel any existing stream
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();

        // Send message with streaming
        let accumulatedContent = "";
        let chunkCount = 0;

        try {
          for await (const chunk of chatApi.streamMessage(
            conversationId,
            messageData,
          )) {
            if (abortControllerRef.current?.signal.aborted) {
              break;
            }

            chunkCount++;
            accumulatedContent += chunk;

            // Update message content
            updateMessage(conversationId, assistantMessageId, {
              content: accumulatedContent,
              streaming: true,
            });

            // Update streaming state
            updateStreaming(accumulatedContent, chunkCount);

            // Track performance
            if (enablePerformanceMonitoring) {
              perf.recordStreamChunk(assistantMessageId, chunk);
            }
          }

          // Mark streaming as complete
          updateMessage(conversationId, assistantMessageId, {
            content: accumulatedContent,
            streaming: false,
          });

          stopStreaming();

          // Record metrics
          if (enablePerformanceMonitoring) {
            const metrics = perf.endStreamMonitoring(assistantMessageId);
            if (metrics) {
              recordMetric(
                "averageResponseTime",
                metrics.completionTime! - metrics.requestStartTime,
              );
              recordMetric("streamingLatency", metrics.averageChunkInterval);
            }
          }

          startTracking();
          setState((prev) => ({ ...prev, isLoading: false }));

          // Call success callback
          onSuccess?.(assistantMessage);

          return assistantMessage;
        } catch (streamError) {
          // Handle streaming errors
          console.error("Streaming failed:", streamError);

          if (enablePerformanceMonitoring) {
            perf.recordStreamError(assistantMessageId, String(streamError));
          }

          // Remove streaming placeholder and try fallback
          const updatedMessages = getMessages(conversationId).filter(
            (msg) => msg.id !== assistantMessageId,
          );

          try {
            // Non-streaming fallback
            const response = await chatApi.sendMessage(
              conversationId,
              messageData,
              false,
            );
            const fallbackMessage: ChatMessage = {
              id: response.id,
              role: response.role,
              content: response.content,
              streaming: false,
            };

            addMessage(conversationId, fallbackMessage);
            setState((prev) => ({ ...prev, isLoading: false }));

            onSuccess?.(fallbackMessage);
            return fallbackMessage;
          } catch (fallbackError) {
            // Both streaming and fallback failed
            const err = new Error(`Message sending failed: ${streamError}`);
            setState((prev) => ({
              ...prev,
              isLoading: false,
              error: err.message,
            }));
            onError?.(err);

            // Remove the failed message placeholder
            const filteredMessages = updatedMessages.filter(
              (msg) => msg.id !== assistantMessageId,
            );
            // Note: In a real implementation, you'd update the store with the filtered messages

            throw err;
          }
        }
      } catch (error) {
        const err =
          error instanceof Error ? error : new Error("Failed to send message");
        setState((prev) => ({ ...prev, isLoading: false, error: err.message }));
        onError?.(err);
        throw err;
      }
    },
    [
      currentConversationId,
      initializeConversation,
      addMessage,
      updateMessage,
      getMessages,
      startStreaming,
      updateStreaming,
      stopStreaming,
      perf,
      enablePerformanceMonitoring,
      recordMetric,
      onError,
      onSuccess,
    ],
  );

  // Streaming controls
  const pauseStreamingHandler = useCallback(async () => {
    if (!currentConversationId || !streaming.currentMessageId) return;

    try {
      await chatApi.controlStreaming(currentConversationId, {
        action: "pause",
        messageId: streaming.currentMessageId,
      });

      pauseStreaming();
      setState((prev) => ({
        ...prev,
        canPauseStream: false,
        canResumeStream: true,
      }));
    } catch (error) {
      console.error("Failed to pause streaming:", error);
    }
  }, [currentConversationId, streaming.currentMessageId, pauseStreaming]);

  const resumeStreamingHandler = useCallback(async () => {
    if (!currentConversationId || !streaming.currentMessageId) return;

    try {
      await chatApi.controlStreaming(currentConversationId, {
        action: "resume",
        messageId: streaming.currentMessageId,
      });

      resumeStreaming();
      setState((prev) => ({
        ...prev,
        canPauseStream: true,
        canResumeStream: false,
      }));
    } catch (error) {
      console.error("Failed to resume streaming:", error);
    }
  }, [currentConversationId, streaming.currentMessageId, resumeStreaming]);

  const stopStreamingHandler = useCallback(async () => {
    if (!currentConversationId || !streaming.currentMessageId) return;

    try {
      await chatApi.controlStreaming(currentConversationId, {
        action: "stop",
        messageId: streaming.currentMessageId,
      });

      abortControllerRef.current?.abort();
      stopStreaming();
      setState((prev) => ({
        ...prev,
        canPauseStream: false,
        canResumeStream: false,
      }));
    } catch (error) {
      console.error("Failed to stop streaming:", error);
    }
  }, [currentConversationId, streaming.currentMessageId, stopStreaming]);

  // Retry failed message
  const retryMessage = useCallback(
    async (messageId: string) => {
      const message = getMessages(currentConversationId || "").find(
        (msg) => msg.id === messageId,
      );
      if (!message || message.role !== "assistant") return;

      try {
        setState((prev) => ({ ...prev, error: null }));

        // Update message to show it's being retried
        updateMessage(currentConversationId!, messageId, {
          content: "",
          streaming: true,
        });

        // Re-send the original message content (this would need to be stored)
        // For now, just mark as failed
        updateMessage(currentConversationId!, messageId, {
          content: "Message failed to send. Please try again.",
          streaming: false,
        });
      } catch (error) {
        const err =
          error instanceof Error ? error : new Error("Failed to retry message");
        setState((prev) => ({ ...prev, error: err.message }));
        onError?.(err);
      }
    },
    [currentConversationId, getMessages, updateMessage, onError],
  );

  // Clear error
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return {
    // State
    state,
    currentConversationId,
    messages: currentConversationId ? getMessages(currentConversationId) : [],

    // Actions
    initializeConversation,
    sendMessage,
    retryMessage,

    // Streaming controls
    pauseStreaming: pauseStreamingHandler,
    resumeStreaming: resumeStreamingHandler,
    stopStreaming: stopStreamingHandler,

    // Utility
    clearError,
  };
};

export type { EnhancedChatState, UseEnhancedChatOptions };
export default useEnhancedChat;
