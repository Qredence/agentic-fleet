import { useState, useRef, useCallback, useEffect } from "react";
import { api } from "../api/client";
import type { Message, StreamEvent, Conversation, Thought } from "../api/types";

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  conversationId: number | string | null;
  conversations: Conversation[];
  createConversation: () => Promise<void>;
  selectConversation: (id: number | string) => Promise<void>;
  loadConversations: () => Promise<void>;
  clearError: () => void;
  thoughts: Thought[];
}

export const useChat = (): UseChatReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | string | null>(
    null,
  );
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (err) {
      console.error("Failed to load conversations:", err);
      // Don't set error for conversation list failures
    }
  }, []);

  const createConversation = useCallback(async () => {
    try {
      setError(null);
      const conv = await api.createConversation("New Chat");
      setConversationId(conv.id);
      setMessages([]);
      setThoughts([]);
      // Refresh conversations list
      await loadConversations();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create conversation";
      console.error("Failed to create conversation:", err);
      setError(errorMessage);
    }
  }, [loadConversations]);

  const selectConversation = useCallback(async (id: number | string) => {
    try {
      setError(null);
      setIsLoading(true);
      const conv = await api.getConversation(id);
      setConversationId(conv.id);
      setMessages(conv.messages || []);
      setThoughts([]);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load conversation";
      console.error("Failed to load conversation:", err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      let currentConvId = conversationId;
      if (!currentConvId) {
        try {
          const conv = await api.createConversation("New Chat");
          currentConvId = conv.id;
          setConversationId(conv.id);
          await loadConversations();
        } catch (error) {
          console.error("Failed to create conversation:", error);
          return;
        }
      }

      // Add user message immediately
      const userMessage: Message = {
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);
      setThoughts([]);

      try {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const response = await api.sendMessage(
          {
            conversation_id: currentConvId,
            message: content,
            stream: true,
          },
          abortControllerRef.current.signal,
        );

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessageContent = "";

        // Add placeholder assistant message
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "",
            created_at: new Date().toISOString(),
          },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") continue;

              try {
                const event: StreamEvent = JSON.parse(data);

                if (event.type === "response.delta" && event.delta) {
                  assistantMessageContent += event.delta;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsg = newMessages[newMessages.length - 1];
                    if (lastMsg.role === "assistant") {
                      lastMsg.content = assistantMessageContent;
                    }
                    return newMessages;
                  });
                } else if (
                  event.type === "orchestrator.thought" &&
                  event.thought
                ) {
                  setThoughts((prev) => [...prev, event.thought!]);
                }
              } catch (e) {
                console.error("Error parsing SSE event:", e);
              }
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          // Request was cancelled, don't treat as error
          return;
        }
        const errorMessage =
          err instanceof Error ? err.message : "Failed to send message";
        console.error("Failed to send message:", err);
        setError(errorMessage);
        // Remove the empty assistant message on error
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg?.role === "assistant" && !lastMsg.content) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [conversationId, loadConversations],
  );

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    conversationId,
    conversations,
    createConversation,
    selectConversation,
    loadConversations,
    clearError,
    thoughts,
  };
};
