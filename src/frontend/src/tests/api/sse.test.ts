/**
 * SSE Client Tests
 *
 * Tests for the ChatSSEClient class that handles real-time streaming.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  ChatSSEClient,
  getSSEClient,
  resetSSEClient,
  type SSEConnectionStatus,
} from "@/api/sse";

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Helper to simulate events
  simulateOpen() {
    this.readyState = 1; // OPEN
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: string) {
    this.onmessage?.(new MessageEvent("message", { data }));
  }

  simulateError() {
    this.readyState = 2; // CLOSED
    this.onerror?.(new Event("error"));
  }

  static get CONNECTING() {
    return 0;
  }
  static get OPEN() {
    return 1;
  }
  static get CLOSED() {
    return 2;
  }
}

// Store original EventSource
const OriginalEventSource = globalThis.EventSource;

describe("ChatSSEClient", () => {
  beforeEach(() => {
    // Mock EventSource globally
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    MockEventSource.instances = [];
    resetSSEClient();
  });

  afterEach(() => {
    globalThis.EventSource = OriginalEventSource;
    resetSSEClient();
  });

  describe("connection lifecycle", () => {
    it("should create EventSource with correct URL", () => {
      const client = new ChatSSEClient();
      client.connect("conv-123", "Hello world");

      expect(MockEventSource.instances).toHaveLength(1);
      const es = MockEventSource.instances[0];
      expect(es.url).toContain("/api/chat/conv-123/stream");
      expect(es.url).toContain("message=Hello+world");
    });

    it("should include optional parameters in URL", () => {
      const client = new ChatSSEClient();
      client.connect("conv-123", "Hello", {
        reasoningEffort: "maximal",
        enableCheckpointing: true,
      });

      const es = MockEventSource.instances[0];
      expect(es.url).toContain("reasoning_effort=maximal");
      expect(es.url).toContain("enable_checkpointing=true");
    });

    it("should update status to connecting then connected", () => {
      const client = new ChatSSEClient();
      const statusChanges: SSEConnectionStatus[] = [];

      client.setCallbacks({
        onStatusChange: (status) => statusChanges.push(status),
      });

      client.connect("conv-123", "Hello");
      expect(client.connectionStatus).toBe("connecting");

      // Simulate connection open
      MockEventSource.instances[0].simulateOpen();
      expect(client.connectionStatus).toBe("connected");
      expect(statusChanges).toEqual(["connecting", "connected"]);
    });

    it("should disconnect and cleanup", () => {
      const client = new ChatSSEClient();
      client.connect("conv-123", "Hello");

      const es = MockEventSource.instances[0];
      const closeSpy = vi.spyOn(es, "close");

      client.disconnect();

      expect(closeSpy).toHaveBeenCalled();
      expect(client.connectionStatus).toBe("disconnected");
      expect(client.isConnected).toBe(false);
    });

    it("should close existing connection before creating new one", () => {
      const client = new ChatSSEClient();

      // First connection
      client.connect("conv-1", "Hello");
      const firstEs = MockEventSource.instances[0];
      const firstCloseSpy = vi.spyOn(firstEs, "close");

      // Second connection
      client.connect("conv-2", "World");

      expect(firstCloseSpy).toHaveBeenCalled();
      expect(MockEventSource.instances).toHaveLength(2);
    });
  });

  describe("event handling", () => {
    it("should parse and emit stream events", () => {
      const client = new ChatSSEClient();
      const events: unknown[] = [];

      client.setCallbacks({
        onEvent: (event) => events.push(event),
      });

      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate a response.delta event
      MockEventSource.instances[0].simulateMessage(
        JSON.stringify({
          type: "response.delta",
          delta: "Hello ",
        }),
      );

      expect(events).toHaveLength(1);
      expect(events[0]).toEqual({
        type: "response.delta",
        delta: "Hello ",
      });
    });

    it("should track workflow_id from connected event", () => {
      const client = new ChatSSEClient();
      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate connected event with workflow_id
      MockEventSource.instances[0].simulateMessage(
        JSON.stringify({
          type: "connected",
          data: { workflow_id: "wf-456" },
        }),
      );

      expect(client.workflowId).toBe("wf-456");
    });

    it("should call onComplete and disconnect on done event", () => {
      const client = new ChatSSEClient();
      const onComplete = vi.fn();

      client.setCallbacks({ onComplete });
      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate done event
      MockEventSource.instances[0].simulateMessage(
        JSON.stringify({ type: "done" }),
      );

      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(client.connectionStatus).toBe("disconnected");
    });

    it("should call onError on error event", () => {
      const client = new ChatSSEClient();
      const onError = vi.fn();

      client.setCallbacks({ onError });
      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate error event
      MockEventSource.instances[0].simulateMessage(
        JSON.stringify({
          type: "error",
          error: "Something went wrong",
        }),
      );

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Something went wrong" }),
      );
    });

    it("should handle cancelled event", () => {
      const client = new ChatSSEClient();
      const onComplete = vi.fn();

      client.setCallbacks({ onComplete });
      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate cancelled event
      MockEventSource.instances[0].simulateMessage(
        JSON.stringify({ type: "cancelled" }),
      );

      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(client.connectionStatus).toBe("disconnected");
    });

    it("should handle connection error", () => {
      const client = new ChatSSEClient();
      const onError = vi.fn();
      const onStatusChange = vi.fn();

      client.setCallbacks({ onError, onStatusChange });
      client.connect("conv-123", "Hello");

      // Simulate connection error (EventSource closed unexpectedly)
      MockEventSource.instances[0].simulateError();

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "SSE connection closed unexpectedly",
        }),
      );
      expect(client.connectionStatus).toBe("error");
    });

    it("should gracefully handle malformed JSON", () => {
      const client = new ChatSSEClient();
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      client.connect("conv-123", "Hello");
      MockEventSource.instances[0].simulateOpen();

      // Simulate malformed message
      MockEventSource.instances[0].simulateMessage("not valid json");

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to parse SSE event:",
        expect.any(Error),
        "not valid json",
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe("singleton management", () => {
    it("should return the same instance from getSSEClient", () => {
      const client1 = getSSEClient();
      const client2 = getSSEClient();

      expect(client1).toBe(client2);
    });

    it("should reset and create new instance", () => {
      const client1 = getSSEClient();
      resetSSEClient();
      const client2 = getSSEClient();

      expect(client1).not.toBe(client2);
    });

    it("should disconnect when resetting", () => {
      const client = getSSEClient();
      client.connect("conv-123", "Hello");

      const es = MockEventSource.instances[0];
      const closeSpy = vi.spyOn(es, "close");

      resetSSEClient();

      expect(closeSpy).toHaveBeenCalled();
    });
  });
});
