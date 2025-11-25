/**
 * Chat Store
 * Manages conversation and message state using Zustand
 */

import { create } from "zustand";
import type { Conversation, Message } from "../lib/api/chatApi";
import * as chatApi from "../lib/api/chatApi";

interface ChatState {
  // State
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  error: string | null;
  streamingContent: string;
  streamingAgentId?: string;
  streamingReasoning?: string;

  // Actions
  loadConversations: () => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation>;
  selectConversation: (conversationId: string) => Promise<void>;
  addMessage: (
    conversationId: string,
    role: "user" | "assistant",
    content: string,
    reasoning?: string,
  ) => void;
  updateLastMessage: (conversationId: string, content: string) => void;
  setStreamingState: (payload: {
    content?: string;
    agentId?: string;
    reasoning?: string;
  }) => void;
  clearStreaming: () => void;
  clearError: () => void;
}

function ensureMessages(conv: Conversation): Conversation {
  return { ...conv, messages: conv.messages || [] };
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversations: [],
  currentConversationId: null,
  isLoading: false,
  error: null,
  streamingContent: "",
  streamingAgentId: undefined,
  streamingReasoning: undefined,

  // Actions
  loadConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const fetchedConversations = (await chatApi.listConversations()).map(
        ensureMessages,
      );

      set((state) => {
        // Keep current conversation if missing from fetched list
        let newConversations = fetchedConversations;

        if (state.currentConversationId) {
          const currentInFetched = newConversations.find(
            (c) => c.id === state.currentConversationId,
          );
          if (!currentInFetched) {
            const currentInState = state.conversations.find(
              (c) => c.id === state.currentConversationId,
            );
            if (currentInState) {
              newConversations = [currentInState, ...newConversations];
            }
          }
        }

        return { conversations: newConversations, isLoading: false };
      });
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to load conversations",
        isLoading: false,
      });
    }
  },

  createConversation: async (title?: string) => {
    set({ isLoading: true, error: null });
    try {
      const conversation = ensureMessages(
        await chatApi.createConversation({ title }),
      );
      set((state) => ({
        conversations: [conversation, ...state.conversations],
        currentConversationId: conversation.id,
        isLoading: false,
      }));
      return conversation;
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to create conversation",
        isLoading: false,
      });
      throw error;
    }
  },

  selectConversation: async (conversationId: string) => {
    // Optimistically switch conversation
    set({ currentConversationId: conversationId, isLoading: true });

    const existing = get().conversations.find((c) => c.id === conversationId);
    // If already have messages, no need to refetch
    if (existing && existing.messages?.length) {
      set({ isLoading: false });
      return;
    }

    try {
      const conversation = ensureMessages(
        await chatApi.getConversation(conversationId),
      );
      set((state) => {
        const others = state.conversations.filter(
          (c) => c.id !== conversationId,
        );
        return {
          conversations: [conversation, ...others],
          isLoading: false,
        };
      });
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to load conversation",
        isLoading: false,
      });
    }
  },

  addMessage: (
    conversationId: string,
    role: "user" | "assistant",
    content: string,
    reasoning?: string,
  ) => {
    set((state) => {
      const conversations = [...state.conversations];
      const index = conversations.findIndex((c) => c.id === conversationId);
      
      if (index !== -1) {
        const message: Message = {
          id: crypto.randomUUID(),
          role,
          content,
          created_at: Date.now() / 1000,
          reasoning,
        };
        conversations[index] = {
          ...conversations[index],
          messages: [...(conversations[index].messages || []), message],
        };
      }
      
      return { conversations };
    });
  },

  updateLastMessage: (conversationId: string, content: string) => {
    set((state) => {
      const conversations = [...state.conversations];
      const index = conversations.findIndex((c) => c.id === conversationId);
      
      if (index !== -1) {
        const messages = [...(conversations[index].messages || [])];
        if (messages.length > 0) {
          messages[messages.length - 1] = {
            ...messages[messages.length - 1],
            content,
          };
          conversations[index] = { ...conversations[index], messages };
        }
      }
      
      return { conversations };
    });
  },

  setStreamingState: ({ content, agentId, reasoning }) => {
    set((state) => ({
      streamingContent: content ?? state.streamingContent,
      streamingAgentId: agentId ?? state.streamingAgentId,
      streamingReasoning: reasoning ?? state.streamingReasoning,
    }));
  },

  clearStreaming: () => {
    set({
      streamingContent: "",
      streamingAgentId: undefined,
      streamingReasoning: undefined,
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
