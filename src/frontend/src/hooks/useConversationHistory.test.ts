import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useConversationHistory } from "./useConversationHistory";
import { API_ENDPOINTS, buildApiUrl } from "../lib/api-config";

// Mock the API config
vi.mock("../lib/api-config", () => ({
  API_ENDPOINTS: {
    CONVERSATION_MESSAGES: (id: string) => `/v1/conversations/${id}/messages`,
  },
  buildApiUrl: (url: string) => `http://localhost:8000${url}`,
}));

describe("useConversationHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should load conversation history successfully", async () => {
    const mockMessages = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "Hello",
      },
      {
        id: "msg-2",
        role: "assistant" as const,
        content: "Hi there",
        actor: "analyst",
      },
    ];

    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ messages: mockMessages }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useConversationHistory());

    let loadedMessages: unknown[] = [];

    await act(async () => {
      loadedMessages = await result.current.loadHistory("conv-123");
    });

    await waitFor(() => {
      expect(loadedMessages).toHaveLength(2);
    });

    expect(loadedMessages).toEqual(mockMessages);
    expect(global.fetch).toHaveBeenCalledWith(
      buildApiUrl(API_ENDPOINTS.CONVERSATION_MESSAGES("conv-123")),
    );
  });

  it("should return empty array on API error", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useConversationHistory());

    let loadedMessages: unknown[] = [];

    await act(async () => {
      loadedMessages = await result.current.loadHistory("conv-123");
    });

    await waitFor(() => {
      expect(loadedMessages).toEqual([]);
    });
  });

  it("should handle network errors gracefully", async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useConversationHistory());

    let loadedMessages: unknown[] = [];

    await act(async () => {
      loadedMessages = await result.current.loadHistory("conv-123");
    });

    await waitFor(() => {
      expect(loadedMessages).toEqual([]);
    });
  });

  it("should handle empty messages array", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ messages: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useConversationHistory());

    let loadedMessages: unknown[] = [];

    await act(async () => {
      loadedMessages = await result.current.loadHistory("conv-123");
    });

    await waitFor(() => {
      expect(loadedMessages).toEqual([]);
    });
  });

  it("should handle missing messages field", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useConversationHistory());

    let loadedMessages: unknown[] = [];

    await act(async () => {
      loadedMessages = await result.current.loadHistory("conv-123");
    });

    await waitFor(() => {
      expect(loadedMessages).toEqual([]);
    });
  });
});
