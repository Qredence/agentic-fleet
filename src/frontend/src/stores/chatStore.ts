import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ChatMessage } from "../features/chat";

export interface StreamingState {
  isStreaming: boolean;
  currentMessageId: string | null;
  agentName: string | null;
  chunkCount: number;
  startTime: number | null;
  estimatedCompletion: number | null;
}

export interface InputState {
  content: string;
  cursorPosition: number;
  isVoiceRecording: boolean;
  uploadedFiles: File[];
  selectedTools: string[];
  lastSaved: number | null;
}

export interface ConversationMetadata {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  agentsInvolved: string[];
  tags: string[];
  isArchived: boolean;
}

export interface ChatFilter {
  agentTypes?: string[];
  dateRange?: { start: Date; end: Date };
  hasAttachments?: boolean;
  isBookmarked?: boolean;
  searchTerm?: string;
}

interface ChatStore {
  // Conversation Management
  conversations: ConversationMetadata[];
  currentConversationId: string | null;
  messages: Record<string, ChatMessage[]>; // conversationId -> messages

  // Streaming State
  streaming: StreamingState;

  // Input State (with persistence)
  input: InputState;

  // Search and Filtering
  activeFilters: ChatFilter;
  searchResults: string[]; // conversation IDs

  // Performance Monitoring
  performanceMetrics: {
    averageResponseTime: number;
    streamingLatency: number;
    errorRate: number;
    totalMessages: number;
  };

  // Actions
  setCurrentConversation: (id: string | null) => void;
  addConversation: (metadata: ConversationMetadata) => void;
  updateConversation: (
    id: string,
    updates: Partial<ConversationMetadata>,
  ) => void;
  deleteConversation: (id: string) => void;

  // Message Management
  addMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (
    conversationId: string,
    messageId: string,
    updates: Partial<ChatMessage>,
  ) => void;
  deleteMessage: (conversationId: string, messageId: string) => void;
  getMessages: (conversationId: string) => ChatMessage[];

  // Streaming Control
  startStreaming: (messageId: string, agentName?: string) => void;
  updateStreaming: (content: string, chunkCount?: number) => void;
  stopStreaming: () => void;
  pauseStreaming: () => void;
  resumeStreaming: () => void;

  // Input Management
  updateInput: (updates: Partial<InputState>) => void;
  saveInputDraft: () => void;
  clearInput: () => void;
  restoreInputDraft: (conversationId: string) => void;

  // Search and Filter
  setFilters: (filters: ChatFilter) => void;
  searchConversations: (query: string) => void;
  clearFilters: () => void;

  // Performance Tracking
  recordMetric: (
    metric: keyof typeof performanceMetrics,
    value: number,
  ) => void;

  // Utility
  resetStore: () => void;
}

const initialState = {
  conversations: [],
  currentConversationId: null,
  messages: {},
  streaming: {
    isStreaming: false,
    currentMessageId: null,
    agentName: null,
    chunkCount: 0,
    startTime: null,
    estimatedCompletion: null,
  },
  input: {
    content: "",
    cursorPosition: 0,
    isVoiceRecording: false,
    uploadedFiles: [],
    selectedTools: [],
    lastSaved: null,
  },
  activeFilters: {},
  searchResults: [],
  performanceMetrics: {
    averageResponseTime: 0,
    streamingLatency: 0,
    errorRate: 0,
    totalMessages: 0,
  },
};

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setCurrentConversation: (id) => {
        set({ currentConversationId: id });
        // Auto-restore input draft when switching conversations
        if (id) {
          get().restoreInputDraft(id);
        }
      },

      addConversation: (metadata) => {
        set((state) => ({
          conversations: [...state.conversations, metadata],
          messages: {
            ...state.messages,
            [metadata.id]: [],
          },
        }));
      },

      updateConversation: (id, updates) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id
              ? { ...conv, ...updates, updatedAt: Date.now() }
              : conv,
          ),
        }));
      },

      deleteConversation: (id) => {
        set((state) => {
          const newConversations = state.conversations.filter(
            (conv) => conv.id !== id,
          );
          const newMessages = { ...state.messages };
          delete newMessages[id];

          return {
            conversations: newConversations,
            messages: newMessages,
            currentConversationId:
              state.currentConversationId === id
                ? null
                : state.currentConversationId,
          };
        });
      },

      addMessage: (conversationId, message) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]: [
              ...(state.messages[conversationId] || []),
              message,
            ],
          },
        }));

        // Update conversation metadata
        get().updateConversation(conversationId, {
          messageCount: (get().messages[conversationId]?.length || 0) + 1,
        });

        // Track performance
        get().recordMetric("totalMessages", 1);
      },

      updateMessage: (conversationId, messageId, updates) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]:
              state.messages[conversationId]?.map((msg) =>
                msg.id === messageId ? { ...msg, ...updates } : msg,
              ) || [],
          },
        }));
      },

      deleteMessage: (conversationId, messageId) => {
        set((state) => {
          const newMessages = {
            ...state.messages,
            [conversationId]:
              state.messages[conversationId]?.filter(
                (msg) => msg.id !== messageId,
              ) || [],
          };

          // Update message count
          const messageCount = newMessages[conversationId]?.length || 0;
          get().updateConversation(conversationId, { messageCount });

          return { messages: newMessages };
        });
      },

      getMessages: (conversationId) => {
        return get().messages[conversationId] || [];
      },

      startStreaming: (messageId, agentName) => {
        set((state) => ({
          streaming: {
            ...state.streaming,
            isStreaming: true,
            currentMessageId: messageId,
            agentName: agentName || null,
            chunkCount: 0,
            startTime: performance.now(),
            estimatedCompletion: null,
          },
        }));
      },

      updateStreaming: (content, chunkCount) => {
        set((state) => ({
          streaming: {
            ...state.streaming,
            chunkCount: chunkCount || state.streaming.chunkCount + 1,
            // Simple estimation: 100ms per chunk average
            estimatedCompletion: state.streaming.startTime
              ? state.streaming.startTime +
                (chunkCount || state.streaming.chunkCount + 1) * 100
              : null,
          },
        }));
      },

      stopStreaming: () => {
        const { streaming } = get();
        if (streaming.startTime) {
          const duration = performance.now() - streaming.startTime;
          get().recordMetric("streamingLatency", duration);
        }

        set((state) => ({
          streaming: {
            ...state.streaming,
            isStreaming: false,
            currentMessageId: null,
            agentName: null,
            startTime: null,
            estimatedCompletion: null,
          },
        }));
      },

      pauseStreaming: () => {
        set((state) => ({
          streaming: {
            ...state.streaming,
            isStreaming: false,
          },
        }));
      },

      resumeStreaming: () => {
        set((state) => ({
          streaming: {
            ...state.streaming,
            isStreaming: true,
          },
        }));
      },

      updateInput: (updates) => {
        set((state) => ({
          input: { ...state.input, ...updates },
        }));
      },

      saveInputDraft: () => {
        const { currentConversationId, input } = get();
        if (!currentConversationId || !input.content.trim()) return;

        // Save to localStorage per conversation
        const draftKey = `chat-draft-${currentConversationId}`;
        localStorage.setItem(
          draftKey,
          JSON.stringify({
            content: input.content,
            selectedTools: input.selectedTools,
            timestamp: Date.now(),
          }),
        );

        set((state) => ({
          input: { ...state.input, lastSaved: Date.now() },
        }));
      },

      clearInput: () => {
        set((state) => ({
          input: { ...initialState.input },
        }));
      },

      restoreInputDraft: (conversationId) => {
        const draftKey = `chat-draft-${conversationId}`;
        const draft = localStorage.getItem(draftKey);

        if (draft) {
          try {
            const { content, selectedTools, timestamp } = JSON.parse(draft);
            // Only restore if draft is less than 24 hours old
            if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
              set((state) => ({
                input: {
                  ...state.input,
                  content: content || "",
                  selectedTools: selectedTools || [],
                  lastSaved: timestamp,
                },
              }));
            }
          } catch (error) {
            console.warn("Failed to restore input draft:", error);
            localStorage.removeItem(draftKey);
          }
        }
      },

      setFilters: (filters) => {
        set({ activeFilters: filters });
        get().applyFilters();
      },

      searchConversations: (query) => {
        const { conversations, messages } = get();
        const searchResults = conversations
          .filter((conv) => {
            // Search in conversation title
            const titleMatch = conv.title
              .toLowerCase()
              .includes(query.toLowerCase());

            // Search in messages
            const convMessages = messages[conv.id] || [];
            const messageMatch = convMessages.some((msg) =>
              msg.content.toLowerCase().includes(query.toLowerCase()),
            );

            return titleMatch || messageMatch;
          })
          .map((conv) => conv.id);

        set({ searchResults });
      },

      clearFilters: () => {
        set({ activeFilters: {}, searchResults: [] });
      },

      recordMetric: (metric, value) => {
        set((state) => {
          const current = state.performanceMetrics[metric];
          let newValue = value;

          if (
            metric === "averageResponseTime" ||
            metric === "streamingLatency"
          ) {
            // Calculate rolling average
            newValue = (current + value) / 2;
          } else if (metric === "totalMessages") {
            newValue = current + value;
          } else if (metric === "errorRate") {
            // Update error rate as percentage
            newValue =
              (current * (state.performanceMetrics.totalMessages - 1) + value) /
              state.performanceMetrics.totalMessages;
          }

          return {
            performanceMetrics: {
              ...state.performanceMetrics,
              [metric]: newValue,
            },
          };
        });
      },

      resetStore: () => {
        set(initialState);
        // Clear all localStorage drafts
        Object.keys(localStorage).forEach((key) => {
          if (key.startsWith("chat-draft-")) {
            localStorage.removeItem(key);
          }
        });
      },

      applyFilters: () => {
        const { conversations, activeFilters, messages } = get();
        let filtered = conversations;

        if (activeFilters.agentTypes?.length) {
          filtered = filtered.filter((conv) =>
            conv.agentsInvolved.some((agent) =>
              activeFilters.agentTypes!.includes(agent),
            ),
          );
        }

        if (activeFilters.dateRange) {
          const { start, end } = activeFilters.dateRange;
          filtered = filtered.filter(
            (conv) =>
              conv.createdAt >= start.getTime() &&
              conv.createdAt <= end.getTime(),
          );
        }

        if (activeFilters.hasAttachments) {
          filtered = filtered.filter((conv) => {
            const convMessages = messages[conv.id] || [];
            return convMessages.some(
              (msg) => msg.attachments && msg.attachments.length > 0,
            );
          });
        }

        if (activeFilters.isBookmarked) {
          filtered = filtered.filter((conv) =>
            conv.tags.includes("bookmarked"),
          );
        }

        if (activeFilters.searchTerm) {
          const term = activeFilters.searchTerm.toLowerCase();
          filtered = filtered.filter((conv) => {
            const titleMatch = conv.title.toLowerCase().includes(term);
            const convMessages = messages[conv.id] || [];
            const messageMatch = convMessages.some((msg) =>
              msg.content.toLowerCase().includes(term),
            );
            return titleMatch || messageMatch;
          });
        }

        set({ searchResults: filtered.map((conv) => conv.id) });
      },
    }),
    {
      name: "agentic-fleet-chat-store",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        performanceMetrics: state.performanceMetrics,
      }),
    },
  ),
);
