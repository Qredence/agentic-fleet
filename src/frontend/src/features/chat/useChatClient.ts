export type Health = { status: "ok" | "down" };
export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: number;
};
export type Conversation = {
  id: string;
  title: string;
  created_at: number;
  messages: ConversationMessage[];
};
export type ChatResponse = {
  conversation_id: string;
  message: string;
  messages: ConversationMessage[];
};

export async function getHealth(): Promise<Health> {
  const r = await fetch("/v1/health");
  return r.json();
}

export async function createConversation(): Promise<Conversation> {
  const r = await fetch("/v1/conversations", { method: "POST" });
  return r.json();
}

export async function getConversation(
  conversationId: string,
): Promise<Conversation> {
  const r = await fetch(`/v1/conversations/${conversationId}`);
  return r.json();
}

export async function sendChat(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  const r = await fetch("/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  return r.json();
}
