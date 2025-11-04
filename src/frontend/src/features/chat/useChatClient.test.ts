import { describe, expect, it } from "vitest";
import {
  createConversation,
  getConversation,
  getHealth,
  sendChat,
} from "./useChatClient";

// Integration tests using real backend API
// Ensure backend is running at http://localhost:8000 before running these tests

describe("useChatClient - Integration Tests", () => {
  it("getHealth checks backend health status", async () => {
    const result = await getHealth();

    expect(result).toHaveProperty("status");
    expect(["ok", "down"]).toContain(result.status);
  });

  it("createConversation creates a new conversation via API", async () => {
    const result = await createConversation();

    expect(result).toHaveProperty("id");
    expect(result).toHaveProperty("title");
    expect(result).toHaveProperty("created_at");
    expect(result).toHaveProperty("messages");
    expect(Array.isArray(result.messages)).toBe(true);
  });

  it("getConversation retrieves an existing conversation", async () => {
    // First create a conversation
    const created = await createConversation();

    // Then retrieve it
    const result = await getConversation(created.id);

    expect(result.id).toBe(created.id);
    expect(result).toHaveProperty("title");
    expect(result).toHaveProperty("created_at");
    expect(result).toHaveProperty("messages");
  });

  it("sendChat sends a message and receives response", async () => {
    // Create a conversation first
    const conversation = await createConversation();

    // Send a chat message
    const result = await sendChat(conversation.id, "Hello, test message");

    expect(result).toHaveProperty("conversation_id");
    expect(result.conversation_id).toBe(conversation.id);
    expect(result).toHaveProperty("message");
    expect(result).toHaveProperty("messages");
    expect(Array.isArray(result.messages)).toBe(true);
    expect(result.messages.length).toBeGreaterThan(0);
  });
});
