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
 * Centralizes conversation lifecycle bootstrap outside of UI components.
 */
export function useConversationInitialization(
  options: UseConversationInitializationOptions = {},
) {
  const { enabled = true, onSuccess, onError } = options;
  const conversationId = useChatStore((s) => s.conversationId);
  const setConversationId = useChatStore((s) => s.setConversationId);
  const setError = useChatStore((s) => s.setError);
  const [initializing, setInitializing] = useState(false);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!enabled || startedRef.current) return;
    if (conversationId) return; // Already initialized

    startedRef.current = true;
    setInitializing(true);

    (async () => {
      try {
        const conversation = await createConversation();
        setConversationId(conversation.id);
        onSuccess?.(conversation.id);
      } catch (err) {
        const error =
          err instanceof Error
            ? err
            : new Error("Failed to create conversation");
        setError(error.message);
        onError?.(error);
      } finally {
        setInitializing(false);
      }
    })();
  }, [
    enabled,
    conversationId,
    onSuccess,
    onError,
    setConversationId,
    setError,
  ]);

  return { conversationId, initializing };
}
