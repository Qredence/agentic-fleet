import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { useStreamingChat } from "@/hooks/useStreamingChat";
import * as chatApi from "@/lib/api/chatApi";

// Mock chatApi.sendMessageStreaming to return a controlled SSE stream
vi.mock("@/lib/api/chatApi", () => ({
  sendMessageStreaming: vi.fn(),
}));

const encoder = new TextEncoder();

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}

describe("useStreamingChat", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("streams deltas, reasoning, and completion callbacks", async () => {
    const events = [
      "event: response.delta\n",
      'data: {"type":"response.delta","delta":"Hello ","agent_id":"agent-99"}\n\n',
      "event: reasoning.delta\n",
      'data: {"type":"reasoning.delta","reasoning":"because"}\n\n',
      "event: response.delta\n",
      'data: {"type":"response.delta","delta":"world"}\n\n',
      "event: agent.message.complete\n",
      'data: {"type":"agent.message.complete","content":"Hello world","agent_id":"agent-99"}\n\n',
      "data: [DONE]\n\n",
    ];

    vi.mocked(chatApi.sendMessageStreaming).mockResolvedValue(
      makeStream(events),
    );

    let completed = "";
    let reasoning = "";
    let lastDelta = "";

    const { result } = renderHook(() =>
      useStreamingChat({
        onMessageComplete: (content) => {
          completed = content;
        },
        onReasoningDelta: (r) => {
          reasoning = r;
        },
        onDelta: (content) => {
          lastDelta = content;
        },
        onError: (err) => {
          throw err;
        },
      }),
    );

    await act(async () => {
      await result.current.sendMessage("conv-1", "hi");
    });

    await waitFor(() => {
      expect(completed).toBe("Hello world");
    });
    expect(lastDelta).toBe("Hello world");
    expect(reasoning).toContain("because");
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamingContent).toBe("Hello world");
    expect(result.current.currentAgentId).toBe("agent-99");
  });
});
