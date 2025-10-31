import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createConversation, getHealth, sendChat } from "./useChatClient";
import { useChatController } from "./useChatController";

vi.mock("./useChatClient", () => {
  return {
    getHealth: vi.fn(),
    createConversation: vi.fn(),
    sendChat: vi.fn(),
  };
});

const mockedGetHealth = vi.mocked(getHealth);
const mockedCreateConversation = vi.mocked(createConversation);
const mockedSendChat = vi.mocked(sendChat);

describe("useChatController", () => {
  beforeEach(() => {
    vi.resetAllMocks();
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

  it("sends chat messages and updates state with response history", async () => {
    mockedCreateConversation.mockResolvedValue({
      id: "conv-1",
      title: "Test conversation",
      created_at: 123,
      messages: [
        {
          id: "seed-user",
          role: "user",
          content: "Seed",
          created_at: 1,
        },
      ],
    });

    mockedSendChat.mockResolvedValue({
      conversation_id: "conv-1",
      message: "Assistant response",
      messages: [
        {
          id: "m-1",
          role: "user",
          content: "Hello",
          created_at: 1,
        },
        {
          id: "m-2",
          role: "assistant",
          content: "Assistant response",
          created_at: 2,
        },
      ],
    });

    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).toBe("conv-1"));

    await act(async () => {
      await result.current.send("Hello");
    });

    expect(mockedSendChat).toHaveBeenCalledWith("conv-1", "Hello");
    expect(result.current.messages).toEqual([
      { role: "user", content: "Hello" },
      { role: "assistant", content: "Assistant response" },
    ]);
    expect(result.current.pending).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets error when sending message fails", async () => {
    mockedSendChat.mockRejectedValueOnce(new Error("network error"));

    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).toBe("conv-1"));

    await act(async () => {
      await result.current.send("Hello");
    });

    expect(mockedSendChat).toHaveBeenCalledWith("conv-1", "Hello");
    expect(result.current.error).toBe("Failed to send message");
    expect(result.current.pending).toBe(false);
  });
});
