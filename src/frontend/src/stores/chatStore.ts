import {
  createConversation,
  getConversation,
  listConversations,
} from "@/lib/api/chat";
import { streamChatWithStore } from "@/lib/streaming/streamHandlers";
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
    // Abort any active stream before starting a new one
    abortController?.abort();
    abortController = new AbortController();

    await streamChatWithStore(
      conversationId!,
      message,
      {
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
      },
      abortController.signal,
    );
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
      const conversation = await getConversation(conversationId);

      // Map backend messages to frontend ChatMessage format
      const messages: ChatMessage[] = conversation.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        createdAt: msg.created_at,
        reasoning: msg.reasoning || undefined,
      }));

      set({
        conversationId: conversation.id,
        messages,
        error: null,
      });
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
      const response = await listConversations();

      const conversations: Conversation[] = response.items.map((conv) => ({
        id: conv.id,
        title: conv.title,
        created_at: conv.created_at,
        messages: conv.messages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          createdAt: msg.created_at,
          reasoning: msg.reasoning || undefined,
        })),
      }));

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
      const conversation = await createConversation();
      set({
        conversationId: conversation.id,
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
      await get().loadConversations();
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
