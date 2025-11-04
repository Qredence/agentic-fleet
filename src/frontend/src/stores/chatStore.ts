import { createConversation, streamChatResponse } from "@/lib/api/chat";
import type {
  ChatActions,
  ChatMessage,
  ChatState,
  OrchestratorMessage,
} from "@/types/chat";
import { create } from "zustand";

interface ChatStore extends ChatState, ChatActions {}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state
  messages: [],
  currentStreamingMessage: "",
  currentAgentId: undefined,
  currentStreamingMessageId: undefined,
  currentStreamingTimestamp: undefined,
  orchestratorMessages: [],
  isLoading: false,
  error: null,
  conversationId: null,

  // Actions
  sendMessage: async (message: string) => {
    const state = get();

    // Validate input
    if (!message.trim()) {
      return;
    }

    // Ensure we have a conversation ID
    let conversationId = state.conversationId;
    if (!conversationId) {
      try {
        const conversation = await createConversation();
        conversationId = conversation.id;
        set({ conversationId });
      } catch (error) {
        set({
          error:
            error instanceof Error
              ? error.message
              : "Failed to create conversation",
        });
        return;
      }
    }

    // Add user message to state
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      createdAt: Date.now(),
    };

    set({
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
      currentStreamingMessage: "",
      currentAgentId: undefined,
      currentStreamingMessageId: undefined,
      currentStreamingTimestamp: undefined,
    });

    // Stream the response
    try {
      await streamChatResponse(conversationId, message, {
        onDelta: (delta, agentId) => {
          const currentState = get();

          // If agent changed and we have accumulated content, save the previous agent's message
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
            // Same agent or no agent ID change - just accumulate
            set((state) => {
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
              agentId: agentId,
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
          // Only create final message if there's remaining streaming content
          // (this handles the final orchestrator result if any)
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

          set((state) => {
            const existing = state.orchestratorMessages.find(
              (msg) =>
                msg.kind === orchestratorMessage.kind &&
                msg.message === orchestratorMessage.message,
            );

            if (existing) {
              return {};
            }

            return {
              orchestratorMessages: [
                ...state.orchestratorMessages,
                orchestratorMessage,
              ],
              currentStreamingMessageId: state.currentStreamingMessageId,
              currentStreamingTimestamp: state.currentStreamingTimestamp,
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
          });
        },
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to send message",
        isLoading: false,
        currentStreamingMessage: "",
        currentStreamingMessageId: undefined,
        currentStreamingTimestamp: undefined,
      });
    }
  },

  appendDelta: (delta: string, agentId?: string) => {
    set((state) => {
      const timestamp = state.currentStreamingTimestamp ?? Date.now();
      return {
        currentStreamingMessage: state.currentStreamingMessage + delta,
        currentAgentId: agentId || state.currentAgentId,
        currentStreamingMessageId:
          state.currentStreamingMessageId ?? `streaming-${timestamp}`,
        currentStreamingTimestamp: timestamp,
      };
    });
  },

  addMessage: (message: Omit<ChatMessage, "id" | "createdAt">) => {
    const newMessage: ChatMessage = {
      ...message,
      id: `${message.role}-${Date.now()}`,
      createdAt: Date.now(),
    };

    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },

  addOrchestratorMessage: (message: string, kind?: string) => {
    const orchestratorMessage: OrchestratorMessage = {
      id: `orchestrator-${Date.now()}-${Math.random()}`,
      message,
      kind,
      timestamp: Date.now(),
    };

    set((state) => ({
      orchestratorMessages: [
        ...state.orchestratorMessages,
        orchestratorMessage,
      ],
    }));
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  setConversationId: (id: string) => {
    set({ conversationId: id });
  },

  completeStreaming: () => {
    const state = get();
    if (state.currentStreamingMessage) {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: state.currentStreamingMessage,
        createdAt: state.currentStreamingTimestamp ?? Date.now(),
        agentId: state.currentAgentId,
      };

      set({
        messages: [...state.messages, assistantMessage],
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

  reset: () => {
    set({
      messages: [],
      currentStreamingMessage: "",
      currentAgentId: undefined,
      currentStreamingMessageId: undefined,
      currentStreamingTimestamp: undefined,
      orchestratorMessages: [],
      isLoading: false,
      error: null,
      conversationId: null,
    });
  },
}));
