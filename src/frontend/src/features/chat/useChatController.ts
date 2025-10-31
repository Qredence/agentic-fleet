import { useCallback, useEffect, useRef, useState } from "react";
import { createConversation, getHealth } from "./useChatClient";
import { useSSEStream } from "./useSSEStream";

export type ChatMessage = {
  id: string | number;
  role: "user" | "assistant" | "system";
  content: string;
  streaming?: boolean;
};

export function useChatController() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { connect, disconnect } = useSSEStream();
  const streamingMessageRef = useRef<string>("");
  const messageCounterRef = useRef(0);

  useEffect(() => {
    getHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));

    createConversation()
      .then((conv) => {
        setConversationId(conv.id);
        setMessages(
          conv.messages.map((m, index) => ({
            id: `${conv.id}-${index}`,
            role: m.role as ChatMessage["role"],
            content: m.content,
          })),
        );
        messageCounterRef.current = conv.messages.length;
      })
      .catch(() => setError("Failed to create conversation"));

    return () => disconnect();
  }, [disconnect]);

  const send = useCallback(
    (text: string) => {
      if (!conversationId || pending) return;

      setError(null);
      setPending(true);
      streamingMessageRef.current = "";

      // Add user message immediately
      const userMsgId = `${conversationId}-${messageCounterRef.current++}`;
      const assistantMsgId = `${conversationId}-${messageCounterRef.current++}`;

      setMessages((prev) => [
        ...prev,
        {
          id: userMsgId,
          role: "user" as const,
          content: text,
        },
        {
          id: assistantMsgId,
          role: "assistant" as const,
          content: "",
          streaming: true,
        },
      ]);

      // Connect to SSE stream
      const cleanup = connect(conversationId, text, {
        onMessage: (sseMessage) => {
          if (sseMessage.type === "delta" && sseMessage.delta) {
            streamingMessageRef.current += sseMessage.delta;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? { ...msg, content: streamingMessageRef.current }
                  : msg,
              ),
            );
          }
        },
        onError: (err) => {
          console.error("SSE Error:", err);
          setError("Connection error during streaming");
          setPending(false);
          // Mark message as non-streaming on error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, streaming: false } : msg,
            ),
          );
        },
        onComplete: () => {
          setPending(false);
          // Mark message as complete
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, streaming: false } : msg,
            ),
          );
        },
      });

      // Cleanup on unmount or new message
      return cleanup;
    },
    [conversationId, pending, connect],
  );

  return { health, conversationId, messages, pending, error, send };
}
