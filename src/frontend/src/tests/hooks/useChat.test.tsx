import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { useChat } from "../../hooks/useChat";
import { api } from "../../api/client";

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
    (api.createConversation as Mock).mockResolvedValue({ id: "conv-123" });
    (api.listConversations as Mock).mockResolvedValue([]);
    (api.loadConversationMessages as Mock).mockResolvedValue([]);
  });

  it("handles agent events correctly", async () => {
    const streamEvents = [
      {
        type: "response.delta",
        delta: "planner starting sequential step",
        kind: "execution",
        agent_id: "planner",
      },
      { type: "agent.start", message: "Agent started", kind: "info" },
      {
        type: "agent.message",
        message: "What is DSPy? One-sentence elevator pitch...",
        kind: "output",
        agent_id: "writer",
      },
      { type: "agent.thought", message: "Thinking...", kind: "thought" },
      { type: "agent.output", content: "Result", kind: "output" },
      { type: "agent.complete", message: "Done", kind: "success" },
      { type: "response.completed", message: "Final answer" },
    ];

    const stream = new ReadableStream({
      start(controller) {
        streamEvents.forEach((event) => {
          controller.enqueue(
            new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`),
          );
        });
        controller.close();
      },
    });

    (api.sendMessage as Mock).mockResolvedValue({
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    // Wait for hook to finish initializing (loadConversations + createConversation)
    await waitFor(() => {
      expect(result.current.isInitializing).toBe(false);
      expect(result.current.conversationId).toBe("conv-123");
    });

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      // User + placeholder assistant (with steps) + agent message + Final Answer message
      expect(result.current.messages).toHaveLength(4);
    });

    const assistantMsg = result.current.messages[1]; // placeholder assistant that holds steps
    const agentMsg = result.current.messages[2]; // agent message with content
    const finalMsg = result.current.messages[3]; // final answer

    expect(agentMsg.role).toBe("assistant");
    // agent.output replaces content with "Result", so the final content is "Result"
    expect(agentMsg.content).toBe("Result");
    expect(finalMsg.role).toBe("assistant");
    expect(finalMsg.author).toBe("Final Answer");

    // Check steps on the workflow placeholder
    // The placeholder assistant message keeps status + agent_start + agent_complete for lifecycle visibility
    expect(assistantMsg.steps).toBeDefined();
    expect(assistantMsg.steps!.length).toBeGreaterThanOrEqual(2);
    expect(assistantMsg.steps![0].type).toBe("status");
    expect(assistantMsg.steps![0].content).toContain(
      "planner starting sequential step",
    );
    expect(assistantMsg.steps![1].type).toBe("agent_start");
  });
});
