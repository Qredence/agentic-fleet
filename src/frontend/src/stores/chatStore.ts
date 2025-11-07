import { createConversation } from "@/lib/api/chat";
import { streamChatWithStore } from "@/lib/streaming/streamHandlers";
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
  currentReasoningContent: undefined,
  currentReasoningStreaming: false,
  orchestratorMessages: [],
  isLoading: false,
  error: null,
  conversationId: null,

  // Actions
  sendMessage: async (message: string) => {
    const state = get();
    if (!message.trim()) return;
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
    await streamChatWithStore(conversationId!, message, {
      get,
      set,
      completeReasoning: (reasoning: string) =>
        set({
          currentReasoningContent: reasoning,
          currentReasoningStreaming: false,
        }),
      appendReasoningDelta: (reasoning: string) => {
        const state = get();
        set({
          currentReasoningContent:
            (state.currentReasoningContent || "") + reasoning,
          currentReasoningStreaming: true,
        });
      },
    });
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

  appendReasoningDelta: (reasoning: string) => {
    const state = get();
    set({
      currentReasoningContent:
        (state.currentReasoningContent || "") + reasoning,
      currentReasoningStreaming: true,
    });
  },

  completeReasoning: (reasoning: string) => {
    set({
      currentReasoningContent: reasoning,
      currentReasoningStreaming: false,
    });
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
        reasoning: state.currentReasoningContent,
        reasoningStreaming: false,
      };

      set({
        messages: [...state.messages, assistantMessage],
        currentStreamingMessage: "",
        currentAgentId: undefined,
        currentStreamingMessageId: undefined,
        currentStreamingTimestamp: undefined,
        currentReasoningContent: undefined,
        currentReasoningStreaming: false,
        isLoading: false,
      });
    } else {
      set({
        isLoading: false,
        currentStreamingMessageId: undefined,
        currentStreamingTimestamp: undefined,
        currentReasoningContent: undefined,
        currentReasoningStreaming: false,
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
      currentReasoningContent: undefined,
      currentReasoningStreaming: false,
      orchestratorMessages: [],
      isLoading: false,
      error: null,
      conversationId: null,
    });
  },
}));
