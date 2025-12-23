import { conversationsApi } from "@/api/client";
import { getSSEClient } from "@/api/sse";
import { getGlobalToastInstance } from "@/hooks/use-toast";
import { createErrorStep } from "@/lib/step-helpers";
import {
  addStepToLastMessage,
  clearMessageContent,
  handleStreamEvent,
  updateLastAssistantMessage,
} from "./chat-event-handler";
import type { ChatState, SendMessageOptions } from "./types";

type ZustandSet = (
  partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>),
) => void;

interface StartChatTransportParams {
  conversationId: string;
  content: string;
  assistantMessageId: string;
  options?: SendMessageOptions;
  set: ZustandSet;
  get: () => ChatState;
}

export function startChatTransport({
  conversationId,
  content,
  assistantMessageId,
  options,
  set,
  get,
}: StartChatTransportParams): void {
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
      handleStreamEvent(event, set, get, assistantMessageId);
    },

    onComplete: () => {
      clearMessageContent(assistantMessageId);

      set({
        isLoading: false,
        isReasoningStreaming: false,
        currentReasoning: "",
      });

      setTimeout(() => {
        const { conversationId: activeConversationId } = get();
        if (activeConversationId) {
          void conversationsApi
            .getMessages(activeConversationId)
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
      }, 2000);
    },

    onError: (error) => {
      console.error("Stream error:", error);

      const toast = getGlobalToastInstance();

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
        const { message: errorMessage } = formatApiError(error);
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

  sseClient.connect(conversationId, content, {
    reasoningEffort: options?.reasoning_effort,
    enableCheckpointing: options?.enable_checkpointing,
  });
}
