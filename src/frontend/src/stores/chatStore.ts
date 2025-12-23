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
import { formatApiError } from "@/api/error";
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
  clearMessageContent,
  startNewMessage,
  addStepToLastMessage,
} from "./chat-event-handler";
import { startChatTransport } from "./chat-transport";

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

        const { message, validationErrors } = formatApiError(e);
        const errorMessage =
          validationErrors && validationErrors.length > 0
            ? validationErrors.join(", ")
            : message;

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

    startChatTransport({
      conversationId: currentConvId!,
      content,
      assistantMessageId: assistantMessage.id,
      options,
      set,
      get,
    });
  },
});

// Conditionally apply devtools middleware only in development
// This prevents exposing sensitive conversation data in production browser devtools
export const useChatStore = create<ChatState>()(
  import.meta.env.DEV ? devtools(storeImpl, { name: "chat-store" }) : storeImpl,
);
