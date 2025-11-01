import type { Message, ToolCall } from "../hooks/useMessageState";
import type { PendingApproval } from "../hooks/useApprovalWorkflow";

/**
 * Mock data factories for tests
 */

export function createMockMessage(overrides?: Partial<Message>): Message {
  return {
    id: `msg-${Math.random().toString(36).substr(2, 9)}`,
    role: "assistant",
    content: "Test message",
    ...overrides,
  };
}

export function createMockToolCall(overrides?: Partial<ToolCall>): ToolCall {
  return {
    id: `tool-${Math.random().toString(36).substr(2, 9)}`,
    type: "function",
    function: {
      name: "test_function",
      arguments: JSON.stringify({ param: "value" }),
    },
    ...overrides,
  };
}

export function createMockPendingApproval(
  overrides?: Partial<PendingApproval>,
): PendingApproval {
  return {
    id: `approval-${Math.random().toString(36).substr(2, 9)}`,
    operation_type: "test_operation",
    description: "Test approval request",
    details: {},
    ...overrides,
  };
}

export function createMockMessages(count: number): Message[] {
  return Array.from({ length: count }, (_, i) =>
    createMockMessage({
      id: `msg-${i}`,
      content: `Message ${i}`,
      role: i % 2 === 0 ? "user" : "assistant",
    }),
  );
}

/**
 * Mock SSE Event Source
 */
export class MockEventSource {
  static instances: MockEventSource[] = [];
  listeners: Record<string, ((event: MessageEvent) => void)[]> = {};
  readyState = EventSource.CONNECTING;
  url: string;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: (event: MessageEvent) => void,
  ): void {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(listener);
  }

  removeEventListener(
    type: string,
    listener: (event: MessageEvent) => void,
  ): void {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter((l) => l !== listener);
    }
  }

  emit(type: string, data: unknown): void {
    if (this.listeners[type]) {
      const event = new MessageEvent(type, {
        data: typeof data === "string" ? data : JSON.stringify(data),
      });
      this.listeners[type].forEach((listener) => listener(event));
    }
  }

  close(): void {
    this.closed = true;
    this.readyState = EventSource.CLOSED;
  }

  static reset(): void {
    MockEventSource.instances = [];
  }
}
