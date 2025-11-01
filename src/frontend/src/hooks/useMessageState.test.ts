import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useMessageState, type Message } from "./useMessageState";

describe("useMessageState", () => {
  it("should initialize with empty messages", () => {
    const { result } = renderHook(() => useMessageState());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isStreaming()).toBe(false);
  });

  it("should add a message", () => {
    const { result } = renderHook(() => useMessageState());

    const message: Message = {
      id: "msg-1",
      role: "user",
      content: "Hello",
    };

    act(() => {
      result.current.addMessage(message);
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toEqual(message);
  });

  it("should clear all messages", () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.addMessage({
        id: "msg-1",
        role: "user",
        content: "Hello",
      });
      result.current.addMessage({
        id: "msg-2",
        role: "assistant",
        content: "Hi there",
      });
    });

    expect(result.current.messages).toHaveLength(2);

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.isStreaming()).toBe(false);
  });

  it("should start streaming a message", () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.startStreamingMessage("msg-1", "Hello", "assistant");
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("Hello");
    expect(result.current.messages[0].isNew).toBe(true);
    expect(result.current.isStreaming()).toBe(true);
  });

  it("should append delta to streaming message", async () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.startStreamingMessage("msg-1", "Hello", "assistant");
    });

    expect(result.current.messages[0].content).toBe("Hello");

    act(() => {
      result.current.appendDelta(" world");
    });

    // Wait for RAF to flush
    await waitFor(() => {
      expect(result.current.messages[0].content).toBe("Hello world");
    });

    expect(result.current.isStreaming()).toBe(true);
  });

  it("should not append delta if no messages exist", () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.appendDelta("test");
    });

    expect(result.current.messages).toHaveLength(0);
  });

  it("should finish streaming", () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.startStreamingMessage("msg-1", "Hello", "assistant");
    });

    expect(result.current.isStreaming()).toBe(true);

    act(() => {
      result.current.finishStreaming();
    });

    expect(result.current.isStreaming()).toBe(false);
  });

  it("should reset streaming state", () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.startStreamingMessage("msg-1", "Hello", "assistant");
    });

    expect(result.current.isStreaming()).toBe(true);

    act(() => {
      result.current.resetStreaming();
    });

    expect(result.current.isStreaming()).toBe(false);
  });

  it("should set messages directly", () => {
    const { result } = renderHook(() => useMessageState());

    const messages: Message[] = [
      {
        id: "msg-1",
        role: "user",
        content: "Hello",
      },
      {
        id: "msg-2",
        role: "assistant",
        content: "Hi there",
      },
    ];

    act(() => {
      result.current.setMessages(messages);
    });

    expect(result.current.messages).toEqual(messages);
  });

  it("should handle multiple streaming messages sequentially", async () => {
    const { result } = renderHook(() => useMessageState());

    act(() => {
      result.current.startStreamingMessage("msg-1", "First", "assistant");
      result.current.appendDelta(" message");
      result.current.finishStreaming();
    });

    // Wait for RAF flush from appendDelta
    await waitFor(() => {
      expect(result.current.messages[0].content).toBe("First message");
    });

    act(() => {
      result.current.startStreamingMessage("msg-2", "Second", "assistant");
      result.current.appendDelta(" message");
    });

    // Wait for second RAF flush
    await waitFor(() => {
      expect(result.current.messages[1].content).toBe("Second message");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.isStreaming()).toBe(true);
  });
});
