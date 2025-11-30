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
    },
  };
});

describe("useChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.createConversation as Mock).mockResolvedValue({ id: "conv-123" });
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

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(3); // User + placeholder assistant + agent message (completion updates placeholder, doesn't create new)
    });

    const agentMsg = result.current.messages[2];
    const assistantMsg = result.current.messages[1]; // placeholder assistant that holds steps
    expect(agentMsg.role).toBe("assistant");
    expect(agentMsg.content).toContain(
      "What is DSPy? One-sentence elevator pitch",
    );

    // Check steps
    // The placeholder assistant message only keeps the status + agent_start for lifecycle visibility
    expect(assistantMsg.steps).toHaveLength(2);
    expect(assistantMsg.steps![0].type).toBe("status");
    expect(assistantMsg.steps![0].content).toContain(
      "planner starting sequential step",
    );
    expect(assistantMsg.steps![1].type).toBe("agent_start");
  });
});
