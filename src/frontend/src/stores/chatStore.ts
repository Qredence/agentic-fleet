import type {
  ChatActions,
  ChatMessage,
  ChatState,
  Conversation,
  OrchestratorMessage,
} from "@/types/chat";
import { create } from "zustand";

interface ChatStore extends ChatState, ChatActions {}

let abortController: AbortController | null = null;

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
  conversations: [],
  isLoadingConversations: false,

  // Actions
  sendMessage: async (message: string) => {
    const state = get();
    if (!message.trim()) return;

    // Use existing conversation ID or generate a local one
    let conversationId = state.conversationId;
    if (!conversationId) {
      conversationId = `local-${Date.now()}`;
      set({ conversationId });
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

    try {
      // Import client dynamically or use the one we created
      const { apiClient } = await import("@/lib/api/client");

      const response = await apiClient.runWorkflow({
        task: message,
        config: { max_rounds: 10 }, // Default config
      });

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.result,
        createdAt: Date.now(),
        reasoning: response.execution_summary
          ? JSON.stringify(response.execution_summary, null, 2)
          : undefined,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (error) {
      set({
        isLoading: false,
        error:
          error instanceof Error ? error.message : "Failed to run workflow",
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

  loadConversationHistory: async (conversationId: string) => {
    try {
      // Mock implementation
      // In a real app, we would fetch messages for this ID
      // For now, we just set the ID and clear messages or keep existing if it matches
      const state = get();
      if (state.conversationId !== conversationId) {
        set({
          conversationId: conversationId,
          messages: [], // Start fresh or load from local storage if we implemented that
          error: null,
        });
      }
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to load conversation history",
      });
      throw error;
    }
  },

  loadConversations: async () => {
    set({ isLoadingConversations: true });
    try {
      // Mock implementation for now as backend doesn't support conversations yet
      const conversations: Conversation[] = [];

      set({
        conversations,
        isLoadingConversations: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoadingConversations: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to load conversations",
      });
    }
  },

  switchConversation: async (conversationId: string) => {
    const state = get();
    if (state.conversationId === conversationId) {
      return;
    }

    abortController?.abort();
    abortController = null;

    // Load conversation history
    await get().loadConversationHistory(conversationId);

    // Reload conversations list to ensure it's up to date
    await get().loadConversations();
  },

  createNewConversation: async () => {
    // Abort any active stream before creating new conversation
    abortController?.abort();
    abortController = null;

    try {
      // Local only for now
      const conversationId = `local-${Date.now()}`;
      set({
        conversationId,
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
      });
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to create new conversation",
      });
      throw error;
    }
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

  /** Abort active SSE stream and cleanup streaming state */
  cancelStreaming: () => {
    // Abort controller and clear reference
    abortController?.abort();
    abortController = null;

    set({
      isLoading: false,
      currentStreamingMessage: "",
      currentAgentId: undefined,
      currentStreamingMessageId: undefined,
      currentStreamingTimestamp: undefined,
      currentReasoningContent: undefined,
      currentReasoningStreaming: false,
    });
  },

  reset: () => {
    // Abort any active stream on reset
    abortController?.abort();
    abortController = null;

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
      conversations: [],
      isLoadingConversations: false,
    });
  },
}));
