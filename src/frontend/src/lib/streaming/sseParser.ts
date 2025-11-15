export type SSEEvent = {
  type: string;
  [key: string]: unknown;
};

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
