import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createConversation,
  getConversation,
  getHealth,
  sendChat,
} from "@/features/chat/useChatClient";

const originalFetch = globalThis.fetch;

afterEach(() => {
  vi.restoreAllMocks();
  if (originalFetch) {
    globalThis.fetch = originalFetch;
  }
});

function mockResponse(data: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("useChatClient", () => {
  it("getHealth fetches health endpoint and returns parsed JSON", async () => {
    const expected = { status: "ok" } as const;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(mockResponse(expected));

    const result = await getHealth();

    expect(fetchSpy).toHaveBeenCalledWith("/v1/system/health");
    expect(result).toEqual(expected);
  });

  it("createConversation posts to conversations endpoint", async () => {
    const expected = {
      id: "conv-1",
      title: "Test",
      created_at: 123,
      messages: [],
    } as const;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(mockResponse(expected));

    const result = await createConversation();

    expect(fetchSpy).toHaveBeenCalledWith("/v1/conversations", {
      method: "POST",
    });
    expect(result).toEqual(expected);
  });

  it("getConversation retrieves a specific conversation", async () => {
    const expected = {
      id: "conv-2",
      title: "Existing",
      created_at: 456,
      messages: [],
    } as const;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(mockResponse(expected));

    const result = await getConversation("conv-2");

    expect(fetchSpy).toHaveBeenCalledWith("/v1/conversations/conv-2");
    expect(result).toEqual(expected);
  });

  it("sendChat posts chat payload and returns response", async () => {
    const expected = {
      conversation_id: "conv-3",
      message: "A reply",
      messages: [
        {
          id: "m-1",
          role: "user" as const,
          content: "Hi",
          created_at: 1,
        },
        {
          id: "m-2",
          role: "assistant" as const,
          content: "Hello there",
          created_at: 2,
        },
      ],
    };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(mockResponse(expected));

    const result = await sendChat("conv-3", "Hi");

    expect(fetchSpy).toHaveBeenCalledWith("/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: "conv-3", message: "Hi" }),
    });
    expect(result).toEqual(expected);
  });
});
