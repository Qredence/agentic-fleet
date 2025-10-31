import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createConversation, getHealth } from "./useChatClient";
import { useChatController } from "./useChatController";
import { useSSEStream } from "./useSSEStream";

vi.mock("./useChatClient", () => {
  return {
    getHealth: vi.fn(),
    createConversation: vi.fn(),
  };
});

vi.mock("./useSSEStream", () => {
  return {
    useSSEStream: vi.fn(),
  };
});

const mockedGetHealth = vi.mocked(getHealth);
const mockedCreateConversation = vi.mocked(createConversation);
const mockedUseSSEStream = vi.mocked(useSSEStream);

describe("useChatController", () => {
  let mockConnect: ReturnType<typeof vi.fn>;
  let mockDisconnect: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.resetAllMocks();
    mockConnect = vi.fn();
    mockDisconnect = vi.fn();

    mockedUseSSEStream.mockReturnValue({
      connect: mockConnect,
      disconnect: mockDisconnect,
    });

    mockedGetHealth.mockResolvedValue({ status: "ok" });
    mockedCreateConversation.mockResolvedValue({
      id: "conv-1",
      title: "Test conversation",
      created_at: 123,
      messages: [],
    });
  });

  it("initialises health and conversation state on mount", async () => {
    const { result } = renderHook(() => useChatController());

    await waitFor(() => {
      expect(result.current.health).toBe("ok");
      expect(result.current.conversationId).toBe("conv-1");
    });

    expect(mockedGetHealth).toHaveBeenCalledTimes(1);
    expect(mockedCreateConversation).toHaveBeenCalledTimes(1);
    expect(result.current.messages).toEqual([]);
    expect(result.current.pending).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sends chat messages and updates state with streaming", async () => {
    mockedCreateConversation.mockResolvedValue({
      id: "conv-1",
      title: "Test conversation",
      created_at: 123,
      messages: [],
    });

    mockConnect.mockImplementation((conversationId, message, handlers) => {
      // Simulate streaming response
      setTimeout(() => {
        handlers.onMessage({ type: "delta", delta: "Hello " });
        handlers.onMessage({ type: "delta", delta: "World" });
        handlers.onMessage({ type: "done" });
        handlers.onComplete();
      }, 0);
      return vi.fn(); // cleanup function
    });

    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).toBe("conv-1"));

    act(() => {
      result.current.send("Hello");
    });

    await waitFor(() => {
      expect(mockConnect).toHaveBeenCalledWith(
        "conv-1",
        "Hello",
        expect.objectContaining({
          onMessage: expect.any(Function),
          onError: expect.any(Function),
          onComplete: expect.any(Function),
        }),
      );
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBe(2);
      expect(result.current.messages[0]).toMatchObject({
        role: "user",
        content: "Hello",
      });
      expect(result.current.pending).toBe(false);
    });
  });

  it("sets error when SSE connection fails", async () => {
    mockConnect.mockImplementation((conversationId, message, handlers) => {
      setTimeout(() => {
        handlers.onError(new Error("network error"));
      }, 0);
      return vi.fn();
    });

    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).toBe("conv-1"));

    act(() => {
      result.current.send("Hello");
    });

    await waitFor(() => {
      expect(result.current.error).toBe("Connection error during streaming");
      expect(result.current.pending).toBe(false);
    });
  });
});
