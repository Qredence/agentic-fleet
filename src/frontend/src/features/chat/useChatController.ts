import { useEffect, useState } from "react";
import { createConversation, getHealth, sendChat } from "./useChatClient";

export type ChatMessage = {
  id: string | number;
  role: "user" | "assistant" | "system";
  content: string;
};

export function useChatController() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      })
      .catch(() => setError("Failed to create conversation"));
  }, []);

  const send = async (text: string) => {
    if (!conversationId) return;
    setError(null);
    setPending(true);
    try {
      const res = await sendChat(conversationId, text);
      const updated = res.messages.map((m, index) => ({
        id: `${conversationId}-${index}`,
        role: m.role as ChatMessage["role"],
        content: m.content,
      }));
      setMessages(updated);
    } catch {
      setError("Failed to send message");
    } finally {
      setPending(false);
    }
  };

  return { health, conversationId, messages, pending, error, send };
}
