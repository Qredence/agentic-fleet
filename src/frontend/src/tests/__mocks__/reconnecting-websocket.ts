// Mock WebSocket for testing

// Store mock instances globally for test access
export const mockWebSocketInstances: MockReconnectingWebSocket[] = [];

export class MockReconnectingWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  sentMessages: string[] = [];

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(url: string, _protocols?: string | string[], _options?: object) {
    this.url = url;
    mockWebSocketInstances.push(this);
    // Simulate async connection
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) {
        this.onopen(new Event("open"));
      }
    }, 0);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent("close"));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: object) {
    if (this.onmessage) {
      this.onmessage(
        new MessageEvent("message", { data: JSON.stringify(data) }),
      );
    }
  }

  // Helper to simulate error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event("error"));
    }
  }
}

// Helper to get the last WebSocket instance
export function getLastWebSocket(): MockReconnectingWebSocket | undefined {
  return mockWebSocketInstances[mockWebSocketInstances.length - 1];
}

// Helper to reset mock instances
export function resetMockWebSockets() {
  mockWebSocketInstances.length = 0;
}

export default MockReconnectingWebSocket;
