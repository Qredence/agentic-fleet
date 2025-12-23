/**
 * Chat Store
 *
 * Zustand store for chat state management.
 * Uses SSE (Server-Sent Events) for real-time streaming.
 *
 * Benefits of SSE over WebSocket:
 * - Built-in browser auto-reconnect
 * - Works through all proxies/CDNs
 * - Simpler error handling (standard HTTP errors)
 * - No persistent connection management needed
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { conversationsApi } from "@/api/client";
import { getSSEClient, resetSSEClient } from "@/api/sse";
import { ApiRequestError } from "@/api";
import type { Message } from "@/api/types";
import { getGlobalToastInstance } from "@/hooks/use-toast";
import {
  UI_PREFERENCE_KEYS,
  readBoolPreference,
  writeBoolPreference,
  readStringPreference,
  writeStringPreference,
} from "@/lib/preferences";
import { createErrorStep, createStatusStep } from "@/lib/step-helpers";
import type { ChatState } from "./types";
import {
  handleStreamEvent,
  clearMessageContent,
  startNewMessage,
  addStepToLastMessage,
  updateLastAssistantMessage,
} from "./chat-event-handler";

// =============================================================================
// Helpers
// =============================================================================

let messageIdCounter = 0;

function generateMessageId(): string {
  return `msg-${Date.now()}-${++messageIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}

// =============================================================================
// Store
// =============================================================================

// Store implementation (extracted for conditional devtools wrapping)
// Zustand's set can accept either a partial state or a function returning partial state
type ZustandSet = (
  partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>),
) => void;

const storeImpl = (set: ZustandSet, get: () => ChatState): ChatState => ({
  // Initial state
  messages: [],
  conversationId: null,
  showTrace: readBoolPreference(UI_PREFERENCE_KEYS.showTrace, true),
  showRawReasoning: readBoolPreference(
    UI_PREFERENCE_KEYS.showRawReasoning,
    false,
  ),
  executionMode: readStringPreference(
    UI_PREFERENCE_KEYS.executionMode,
    "auto",
  ) as "auto" | "fast" | "standard",
  enableGepa: readBoolPreference(UI_PREFERENCE_KEYS.enableGepa, false),
  isLoading: false,
  isInitializing: false,
  currentReasoning: "",
  isReasoningStreaming: false,
  currentWorkflowPhase: "",
  currentAgent: null,
  completedPhases: [],
  isConcurrentError: false,

  // =======================
  // Conversation Actions
  // =======================

  selectConversation: async (id: string) => {
    try {
      // Stop any active stream before switching conversations.
      get().cancelStreaming();
      const convMessages = await conversationsApi.getMessages(id);
      set({
        conversationId: id,
        messages: convMessages,
        currentReasoning: "",
        isReasoningStreaming: false,
        currentWorkflowPhase: "",
        currentAgent: null,
        completedPhases: [],
        isLoading: false,
      });
    } catch (error) {
      console.error("Failed to load conversation:", error);
      const toast = getGlobalToastInstance();
      toast?.toast({
        title: "Failed to Load Conversation",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  },

  // =======================
  // Streaming Actions
  // =======================

  cancelStreaming: () => {
    const sseClient = getSSEClient();
    void sseClient.cancel();

    // Clear any accumulated content for the currently streaming assistant message.
    const lastAssistantId = (() => {
      const msgs = get().messages;
      for (let i = msgs.length - 1; i >= 0; i -= 1) {
        if (msgs[i]?.role === "assistant" && msgs[i].id) return msgs[i].id;
      }
      return undefined;
    })();
    clearMessageContent(lastAssistantId);

    set({
      isLoading: false,
      isReasoningStreaming: false,
      currentWorkflowPhase: "",
      currentAgent: null,
      isConcurrentError: false,
    });
  },

  sendWorkflowResponse: (requestId: string, response: unknown) => {
    const sseClient = getSSEClient();
    if (!sseClient.isConnected) {
      const errorStep = createErrorStep(
        "Cannot send workflow response: not connected to stream",
        { request_id: requestId },
      );
      set((state) => addStepToLastMessage(state, errorStep, false));
      return;
    }

    // Submit response via HTTP POST (SSE is read-only, so we use REST for sends)
    void sseClient.submitResponse(requestId, response).catch((err) => {
      console.error("Failed to submit workflow response:", err);
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      const toast = getGlobalToastInstance();
      toast?.toast({
        title: "Failed to Send Response",
        description: errorMessage,
        variant: "destructive",
      });
      const errorStep = createErrorStep(
        `Failed to send response: ${errorMessage}`,
        { request_id: requestId },
      );
      set((state) => addStepToLastMessage(state, errorStep, false));
    });

    const statusStep = createStatusStep("Sent workflow response", "request", {
      request_id: requestId,
    });

    set((state) => addStepToLastMessage(state, statusStep));
  },

  setMessages: (messages) => set({ messages }),

  setShowTrace: (show) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.showTrace, show);
    set({ showTrace: show });
  },

  setShowRawReasoning: (show) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.showRawReasoning, show);
    set({ showRawReasoning: show });
  },

  setExecutionMode: (mode) => {
    writeStringPreference(UI_PREFERENCE_KEYS.executionMode, mode);
    set({ executionMode: mode });
  },

  setEnableGepa: (enable) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.enableGepa, enable);
    set({ enableGepa: enable });
  },

  reset: () => {
    // Disconnect and reset the SSE client singleton
    resetSSEClient();
    // Clear any accumulated message content
    // Note: We don't have a clearAllMessageContent exposed yet, but individual message clearing happens on complete/cancel.
    // Ideally we should clear all map entries here.

    set({
      messages: [],
      conversationId: null,
      isLoading: false,
      currentReasoning: "",
      isReasoningStreaming: false,
      currentWorkflowPhase: "",
      currentAgent: null,
      isConcurrentError: false,
    });
  },

  // =======================
  // Send Message
  // =======================

  sendMessage: async (content, options) => {
    if (!content.trim()) return;

    const { conversationId } = get();
    let currentConvId = conversationId;

    // Create conversation if needed
    if (!currentConvId) {
      try {
        const conv = await conversationsApi.create("New Chat");
        currentConvId = conv.conversation_id;
        set({ conversationId: conv.conversation_id });
        // Note: Conversation list is managed by React Query and will auto-refresh
      } catch (e) {
        console.error("Failed to create conversation:", e);
        const toast = getGlobalToastInstance();

        // Extract error message from ApiRequestError or standard Error
        let errorMessage = "Unknown error occurred";
        if (e instanceof ApiRequestError) {
          errorMessage = e.message;
          // Extract validation errors from FastAPI 422 responses
          if (
            e.details?.validation_errors &&
            e.details.validation_errors.length > 0
          ) {
            errorMessage = e.details.validation_errors
              .map((err) => `${err.field}: ${err.message}`)
              .join(", ");
          }
        } else if (e instanceof Error) {
          errorMessage = e.message;
        } else if (typeof e === "object" && e !== null) {
          // Fallback for non-Error objects
          const errorObj = e as {
            message?: string;
            detail?: string;
            error?: string;
          };
          errorMessage =
            errorObj.message || errorObj.detail || errorObj.error || String(e);
        }

        toast?.toast({
          title: "Failed to Create Conversation",
          description: errorMessage,
          variant: "destructive",
        });
        return;
      }
    }

    // Create optimistic messages
    const groupId = `group-${Date.now()}`;
    const userMessage: Message = {
      id: generateMessageId(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    const assistantMessage: Message = {
      id: generateMessageId(),
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      steps: [],
      groupId,
      isWorkflowPlaceholder: true,
      workflowPhase: "Starting...",
    };

    // Initialize message-scoped content tracking (fixes race condition)
    startNewMessage(assistantMessage.id);

    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      isLoading: true,
      currentWorkflowPhase: "Starting...",
      currentAgent: null,
      currentReasoning: "",
      completedPhases: [],
    }));

    // Setup SSE client callbacks
    const sseClient = getSSEClient();
    sseClient.setCallbacks({
      onStatusChange: (status) => {
        if (status === "error") {
          const toast = getGlobalToastInstance();
          toast?.toast({
            title: "Connection Error",
            description:
              "Failed to connect to the server. Please check your connection and try again.",
            variant: "destructive",
            duration: 7000,
          });

          set((state) => ({
            ...updateLastAssistantMessage(state, () => ({
              isWorkflowPlaceholder: false,
              content: "Connection failed. Please try again.",
              workflowPhase: "",
            })),
            isLoading: false,
          }));
        }
      },

      onEvent: (event) => {
        handleStreamEvent(event, set, get, assistantMessage.id);
      },

      onComplete: () => {
        // Clean up message content tracking
        clearMessageContent(assistantMessage.id);

        set({
          isLoading: false,
          isReasoningStreaming: false,
          currentReasoning: "",
        });

        // Refresh messages after a short delay to pick up quality scores
        // Background evaluation completes asynchronously, so we poll for updates
        setTimeout(() => {
          const { conversationId } = get();
          if (conversationId) {
            // Use React Query to refetch messages if available
            // Otherwise, manually reload from API
            void conversationsApi
              .getMessages(conversationId)
              .then((updatedMessages) => {
                set({ messages: updatedMessages });
              })
              .catch((err) => {
                console.debug(
                  "Failed to refresh messages for quality scores:",
                  err,
                );
              });
          }
        }, 2000); // Wait 2 seconds for background evaluation to complete
      },

      onError: (error) => {
        console.error("Stream error:", error);

        const toast = getGlobalToastInstance();

        // Detect concurrent execution error
        const isConcurrent =
          error.message.includes("Concurrent executions") ||
          error.message.includes("lock");

        if (isConcurrent) {
          toast?.toast({
            title: "Concurrent Execution",
            description:
              "Another workflow is already running. Please wait for it to complete or cancel it first.",
            variant: "warning",
            duration: 8000,
          });
          set({ isConcurrentError: true, isLoading: false });
        } else {
          // Show toast for non-concurrent errors
          const errorMessage = error.message || "Unknown error";
          toast?.toast({
            title: "Stream Error",
            description: errorMessage,
            variant: "destructive",
            duration: 7000,
          });

          const errorStep = createErrorStep(errorMessage);
          set((state) => ({
            ...addStepToLastMessage(state, errorStep, false),
            isLoading: false,
            isReasoningStreaming: false,
          }));
        }
      },
    });

    // Connect via SSE (simpler than WebSocket - just GET with query params)
    sseClient.connect(currentConvId!, content, {
      reasoningEffort: options?.reasoning_effort,
      enableCheckpointing: options?.enable_checkpointing,
    });
  },
});

// Conditionally apply devtools middleware only in development
// This prevents exposing sensitive conversation data in production browser devtools
export const useChatStore = create<ChatState>()(
  import.meta.env.DEV ? devtools(storeImpl, { name: "chat-store" }) : storeImpl,
);
