import { describe, expect, it } from "vitest";
import { parseSSEStream } from "@/lib/streamParser";

const encoder = new TextEncoder();

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}

describe("parseSSEStream", () => {
  it("parses named events, multi-line data, and preserves agent ids", async () => {
    const events: unknown[] = [];
    const stream = makeStream([
      'event: orchestrator.message\n',
      'data: {"type":"orchestrator.message","message":"thinking","kind":"thought"}\n\n',
      'event: response.delta\n',
      'data: {"type":"response.delta","delta":"Hello ","agent_id":"agent-42"}\n\n',
      'event: response.delta\n',
      'data: {"type":"response.delta","delta":"world"}\n\n',
      'event: reasoning.delta\n',
      'data: {"type":"reasoning.delta","reasoning":"why"}\n\n',
      'event: agent.message.complete\n',
      'data: {"type":"agent.message.complete","content":"Hello world","agent_id":"agent-42"}\n\n',
      'data: [DONE]\n\n',
    ]);

    await parseSSEStream(
      stream,
      (evt) => events.push(evt),
      (err) => {
        throw err;
      },
    );

    expect(events.length).toBe(6);
    expect(events[0]).toMatchObject({
      type: "orchestrator.message",
      message: "thinking",
      kind: "thought",
    });
    expect(events[1]).toMatchObject({
      type: "response.delta",
      delta: "Hello ",
      agent_id: "agent-42",
    });
    expect(events[4]).toMatchObject({
      type: "agent.message.complete",
      content: "Hello world",
      agent_id: "agent-42",
    });
    expect(events[5]).toMatchObject({ type: "done" });
  });
});
