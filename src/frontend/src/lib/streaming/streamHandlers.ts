import { streamChatResponse } from "@/lib/api/chat";
import type { ChatMessage, ChatState, OrchestratorMessage } from "@/types/chat";

interface StoreApi {
  get: () => ChatState;
  set: (
    partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>),
  ) => void;
  completeReasoning: (reasoning: string) => void;
  appendReasoningDelta: (reasoning: string) => void;
}

/**
 * Orchestrates streaming chat response handling, mutating store via provided set/get.
 * Extracted from original store.sendMessage for testability & separation of concerns.
 */
export async function streamChatWithStore(
  conversationId: string,
  userMessage: string,
  store: StoreApi,
) {
  const { get, set } = store;

  try {
    await streamChatResponse(conversationId, userMessage, {
      onDelta: (delta, agentId) => {
        const currentState = get();
        // Agent switched mid-stream: persist previous agent's accumulated content
        if (
          agentId &&
          currentState.currentAgentId &&
          agentId !== currentState.currentAgentId
        ) {
          if (currentState.currentStreamingMessage) {
            const agentMessage: ChatMessage = {
              id: `assistant-${
                currentState.currentStreamingTimestamp ?? Date.now()
              }`,
              role: "assistant",
              content: currentState.currentStreamingMessage,
              createdAt: currentState.currentStreamingTimestamp ?? Date.now(),
              agentId: currentState.currentAgentId,
            };
            const timestamp = Date.now();
            set({
              messages: [...currentState.messages, agentMessage],
              currentStreamingMessage: delta,
              currentAgentId: agentId,
              currentStreamingMessageId: `streaming-${timestamp}`,
              currentStreamingTimestamp: timestamp,
            });
          } else {
            const timestamp = Date.now();
            set({
              currentStreamingMessage: delta,
              currentAgentId: agentId,
              currentStreamingMessageId: `streaming-${timestamp}`,
              currentStreamingTimestamp: timestamp,
            });
          }
        } else {
          // Same agent or unknown agent – accumulate delta
          set((state: ChatState) => {
            const timestamp = state.currentStreamingTimestamp ?? Date.now();
            return {
              currentStreamingMessage: state.currentStreamingMessage + delta,
              currentAgentId: agentId || state.currentAgentId,
              currentStreamingMessageId:
                state.currentStreamingMessageId ?? `streaming-${timestamp}`,
              currentStreamingTimestamp: timestamp,
            };
          });
        }
      },
      onAgentComplete: (agentId, content) => {
        const currentState = get();
        const messageContent =
          currentState.currentAgentId === agentId &&
          currentState.currentStreamingMessage
            ? currentState.currentStreamingMessage
            : content;
        if (messageContent) {
          const agentMessage: ChatMessage = {
            id: `assistant-${
              currentState.currentStreamingTimestamp ?? Date.now()
            }`,
            role: "assistant",
            content: messageContent,
            createdAt: currentState.currentStreamingTimestamp ?? Date.now(),
            agentId,
          };
          set({
            messages: [...currentState.messages, agentMessage],
            currentStreamingMessage: "",
            currentAgentId: undefined,
            currentStreamingMessageId: undefined,
            currentStreamingTimestamp: undefined,
          });
        } else {
          set({
            currentStreamingMessage: "",
            currentAgentId: undefined,
            currentStreamingMessageId: undefined,
            currentStreamingTimestamp: undefined,
          });
        }
      },
      onCompleted: () => {
        const currentState = get();
        if (currentState.currentStreamingMessage) {
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: currentState.currentStreamingMessage,
            createdAt: currentState.currentStreamingTimestamp ?? Date.now(),
            agentId: currentState.currentAgentId,
          };
          set({
            messages: [...currentState.messages, assistantMessage],
            currentStreamingMessage: "",
            currentAgentId: undefined,
            currentStreamingMessageId: undefined,
            currentStreamingTimestamp: undefined,
            isLoading: false,
          });
        } else {
          set({
            isLoading: false,
            currentStreamingMessageId: undefined,
            currentStreamingTimestamp: undefined,
          });
        }
      },
      onOrchestrator: (message, kind) => {
        const orchestratorMessage: OrchestratorMessage = {
          id: `orchestrator-${Date.now()}-${Math.random()}`,
          message,
          kind,
          timestamp: Date.now(),
        };
        set((state: ChatState) => {
          const exists = state.orchestratorMessages.find(
            (m: OrchestratorMessage) =>
              m.kind === orchestratorMessage.kind &&
              m.message === orchestratorMessage.message,
          );
          if (exists) return {};
          return {
            orchestratorMessages: [
              ...state.orchestratorMessages,
              orchestratorMessage,
            ],
          };
        });
      },
      onError: (error) => {
        set({
          error,
          isLoading: false,
          currentStreamingMessage: "",
          currentStreamingMessageId: undefined,
          currentStreamingTimestamp: undefined,
          currentReasoningContent: undefined,
          currentReasoningStreaming: false,
        });
      },
      onReasoningCompleted: (reasoning) => {
        store.completeReasoning(reasoning);
      },
    });
  } catch (err) {
    set({
      error: err instanceof Error ? err.message : "Failed to stream message",
      isLoading: false,
      currentStreamingMessage: "",
      currentStreamingMessageId: undefined,
      currentStreamingTimestamp: undefined,
      currentReasoningContent: undefined,
      currentReasoningStreaming: false,
    });
  }
}
