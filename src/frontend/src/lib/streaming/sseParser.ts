export type SSEEvent =
  | {
      type: "response.delta";
      delta: string;
      agent_id?: string;
      agentId?: string;
    }
  | { type: "response.completed" }
  | { type: "orchestrator.message"; message: string; kind?: string }
  | {
      type: "agent.message.complete";
      agent_id?: string;
      agentId?: string;
      content: string;
    }
  | { type: "reasoning.delta"; reasoning: string }
  | { type: "reasoning.completed"; reasoning?: string }
  | { type: "error"; error: string }
  | { type: "__done__" };

export function parseSSELine(line: string): SSEEvent | null {
  if (!line.startsWith("data: ")) return null;
  const data = line.slice(6).trim();
  if (data === "[DONE]") return { type: "__done__" };
  if (data.startsWith(":")) return null;
  try {
    return JSON.parse(data) as SSEEvent;
  } catch {
    return null;
  }
}

export function processBuffer(
  buffer: string,
  onEvent: (e: SSEEvent) => void,
): string {
  const lines = buffer.split("\n");
  const tail = lines.pop() || "";
  for (const line of lines) {
    const evt = parseSSELine(line);
    if (evt) onEvent(evt);
  }
  return tail;
}
