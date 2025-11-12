import { createConversation } from "@/lib/api/chat";
import { useChatStore } from "@/stores/chatStore";
import { useEffect, useRef, useState } from "react";

interface UseConversationInitializationOptions {
  /** Disable automatic initialization */
  enabled?: boolean;
  /** Callback when a new conversation is created */
  onSuccess?: (conversationId: string) => void;
  /** Callback when initialization fails */
  onError?: (error: Error) => void;
}

/**
 * Hook to ensure a conversation exists. Creates one on mount if missing.
 * If a conversationId exists but messages are empty, loads conversation history.
 * Centralizes conversation lifecycle bootstrap outside of UI components.
 */
export function useConversationInitialization(
  options: UseConversationInitializationOptions = {},
) {
  const { enabled = true, onSuccess, onError } = options;
  const conversationId = useChatStore((s) => s.conversationId);
  const messages = useChatStore((s) => s.messages);
  const setConversationId = useChatStore((s) => s.setConversationId);
  const loadConversationHistory = useChatStore(
    (s) => s.loadConversationHistory,
  );
  const setError = useChatStore((s) => s.setError);
  const [initializing, setInitializing] = useState(false);
  const startedRef = useRef(false);
  const loadingHistoryRef = useRef(false);

  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onSuccessRef.current = onSuccess;
    onErrorRef.current = onError;
  });

  // Load conversation history if conversationId exists but messages are empty
  useEffect(() => {
    if (!enabled || loadingHistoryRef.current) return;
    if (!conversationId) return; // No conversationId, will be handled by creation effect
    if (messages.length > 0) return; // Already has messages

    loadingHistoryRef.current = true;
    setInitializing(true);

    (async () => {
      try {
        await loadConversationHistory(conversationId);
        onSuccessRef.current?.(conversationId);
      } catch (err) {
        const error =
          err instanceof Error
            ? err
            : new Error("Failed to load conversation history");
        // Don't set error if conversation not found - might be a new conversation
        if (!error.message.includes("not found")) {
          setError(error.message);
        }
        onErrorRef.current?.(error);
      } finally {
        setInitializing(false);
        loadingHistoryRef.current = false;
      }
    })();
  }, [
    enabled,
    conversationId,
    messages.length,
    loadConversationHistory,
    onSuccess,
    onError,
    setError,
  ]);

  // Create new conversation if conversationId doesn't exist
  useEffect(() => {
    if (!enabled || startedRef.current) return;
    if (conversationId) return; // Already initialized

    startedRef.current = true;
    setInitializing(true);

    (async () => {
      try {
        const conversation = await createConversation();
        setConversationId(conversation.id);
        onSuccessRef.current?.(conversation.id);
      } catch (err) {
        const error =
          err instanceof Error
            ? err
            : new Error("Failed to create conversation");
        setError(error.message);
        onErrorRef.current?.(error);
      } finally {
        setInitializing(false);
      }
    })();
  }, [enabled, conversationId, setConversationId, setError]);

  return { conversationId, initializing };
}
