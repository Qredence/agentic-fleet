import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { useChat } from "../../hooks/useChat";
import { api } from "../../api/client";
import {
  getLastWebSocket,
  resetMockWebSockets,
} from "../__mocks__/reconnecting-websocket";

// Mock reconnecting-websocket using the mock file
vi.mock(
  "reconnecting-websocket",
  () => import("../__mocks__/reconnecting-websocket"),
);

// Mock the api client
vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createConversation: vi.fn(),
      sendMessage: vi.fn(),
      listConversations: vi.fn(),
      loadConversationMessages: vi.fn(),
    },
  };
});

describe("useChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetMockWebSockets();
    (api.createConversation as Mock).mockResolvedValue({ id: "conv-123" });
    (api.listConversations as Mock).mockResolvedValue([]);
    (api.loadConversationMessages as Mock).mockResolvedValue([]);
  });

  it("initializes and creates a conversation", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.isInitializing).toBe(false);
      expect(result.current.conversationId).toBe("conv-123");
    });

    expect(api.listConversations).toHaveBeenCalled();
    expect(api.createConversation).toHaveBeenCalledWith("New Chat");
  });

  it("loads existing conversations on init", async () => {
    (api.listConversations as Mock).mockResolvedValue([
      {
        id: "existing-conv",
        title: "Old Chat",
        updated_at: new Date().toISOString(),
      },
    ]);
    (api.loadConversationMessages as Mock).mockResolvedValue([
      {
        id: "msg-1",
        role: "user",
        content: "Hello",
        created_at: new Date().toISOString(),
      },
    ]);

    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.isInitializing).toBe(false);
      expect(result.current.conversationId).toBe("existing-conv");
      expect(result.current.messages).toHaveLength(1);
    });
  });

  it("sends message via WebSocket", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      result.current.sendMessage("Hello, world!");
    });

    // Wait for WebSocket to be created and opened
    await waitFor(() => {
      const ws = getLastWebSocket();
      expect(ws).toBeDefined();
      expect(ws!.sentMessages.length).toBeGreaterThan(0);
    });

    const ws = getLastWebSocket()!;
    const sentMessage = JSON.parse(ws.sentMessages[0]);

    expect(sentMessage.conversation_id).toBe("conv-123");
    expect(sentMessage.message).toBe("Hello, world!");
    expect(sentMessage.stream).toBe(true);
  });

  it("handles agent events correctly", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      result.current.sendMessage("Hello");
    });

    // Wait for WebSocket connection
    await waitFor(() => {
      const ws = getLastWebSocket();
      expect(ws).toBeDefined();
      expect(ws!.readyState).toBe(1); // OPEN
    });

    const ws = getLastWebSocket()!;

    // Simulate stream events
    await act(async () => {
      ws.simulateMessage({
        type: "response.delta",
        delta: "planner starting sequential step",
        kind: "execution",
        agent_id: "planner",
      });
    });

    await act(async () => {
      ws.simulateMessage({
        type: "agent.start",
        message: "Agent started",
        kind: "info",
      });
    });

    await act(async () => {
      ws.simulateMessage({
        type: "agent.message",
        message: "What is DSPy? One-sentence elevator pitch...",
        kind: "output",
        agent_id: "writer",
      });
    });

    await act(async () => {
      ws.simulateMessage({
        type: "response.completed",
        message: "Final answer",
      });
    });

    await act(async () => {
      ws.simulateMessage({ type: "done" });
      ws.close();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Check messages structure
    expect(result.current.messages.length).toBeGreaterThanOrEqual(3);

    // First message should be user
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("Hello");

    // Check that we have steps recorded
    const assistantMessages = result.current.messages.filter(
      (m) => m.role === "assistant",
    );
    expect(assistantMessages.length).toBeGreaterThan(0);

    // Find message with steps
    const msgWithSteps = assistantMessages.find(
      (m) => m.steps && m.steps.length > 0,
    );
    expect(msgWithSteps).toBeDefined();
    expect(msgWithSteps!.steps![0].type).toBe("status");
  });

  it("cancels streaming by sending cancel message", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      const ws = getLastWebSocket();
      expect(ws).toBeDefined();
      expect(ws!.readyState).toBe(1); // OPEN
    });

    const ws = getLastWebSocket()!;

    // Cancel the streaming
    await act(async () => {
      result.current.cancelStreaming();
    });

    // Check that cancel message was sent
    expect(ws.sentMessages).toContainEqual(JSON.stringify({ type: "cancel" }));
    expect(result.current.isLoading).toBe(false);
  });

  it("handles WebSocket errors gracefully", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      const ws = getLastWebSocket();
      expect(ws).toBeDefined();
    });

    const ws = getLastWebSocket()!;

    // Simulate error
    await act(async () => {
      ws.simulateError();
      ws.close();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Check error message was added
    const lastMessage =
      result.current.messages[result.current.messages.length - 1];
    expect(lastMessage.role).toBe("assistant");
    expect(lastMessage.content).toContain("Sorry, something went wrong");
  });

  it("handles reasoning events", async () => {
    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      result.current.sendMessage("Think about this");
    });

    await waitFor(() => {
      const ws = getLastWebSocket();
      expect(ws).toBeDefined();
      expect(ws!.readyState).toBe(1); // OPEN
    });

    const ws = getLastWebSocket()!;

    await act(async () => {
      ws.simulateMessage({
        type: "reasoning.delta",
        reasoning: "Let me think...",
        agent_id: "planner",
      });
    });

    await waitFor(() => {
      expect(result.current.isReasoningStreaming).toBe(true);
      expect(result.current.currentReasoning).toContain("Let me think");
    });

    await act(async () => {
      ws.simulateMessage({ type: "reasoning.completed" });
    });

    await waitFor(() => {
      expect(result.current.isReasoningStreaming).toBe(false);
    });
  });
});
