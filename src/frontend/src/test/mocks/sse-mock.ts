/**
 * Mock EventSource for testing SSE connections
 */

import type { AnySSEEvent } from "../../lib/types/contracts";

export class MockEventSource {
  readonly CONNECTING = 0 as const;
  readonly OPEN = 1 as const;
  readonly CLOSED = 2 as const;

  readyState: 0 | 1 | 2 = this.CONNECTING;
  url: string;
  withCredentials = false;

  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => this.simulateOpen(), 10);
  }

  simulateOpen(): void {
    this.readyState = this.OPEN;
    if (this.onopen) {
      this.onopen(new Event("open"));
    }
  }

  simulateMessage(data: AnySSEEvent | string): void {
    if (this.onmessage && this.readyState === this.OPEN) {
      const payload = typeof data === "string" ? data : JSON.stringify(data);
      this.onmessage(
        new MessageEvent("message", {
          data: payload,
        })
      );
    }
  }

  simulateError(error?: Error): void {
    this.readyState = this.CLOSED;
    if (this.onerror) {
      const errorEvent = new Event("error");
      if (error) {
        Object.defineProperty(errorEvent, "error", { value: error });
      }
      this.onerror(errorEvent);
    }
  }

  close(): void {
    this.readyState = this.CLOSED;
  }

  addEventListener(_type: string, _listener: EventListenerOrEventListenerObject): void {
    // Simplified for mocking
  }

  removeEventListener(_type: string, _listener: EventListenerOrEventListenerObject): void {
    // Simplified for mocking
  }

  dispatchEvent(_event: Event): boolean {
    return true;
  }
}

/**
 * Mock SSE scenario data for testing
 */
export const mockSSEScenarios = {
  /**
   * Successful chat flow with multiple agents
   */
  successfulChat: [
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "I will help you with that. Let me gather some information...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "tool_call",
      tool: "web_search",
      args: { query: "test query" },
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "researcher",
      content: "I found relevant information...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "progress",
      step: "research",
      progress: 0.5,
      message: "Researching...",
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "analyst",
      content: "Based on the research, here is my analysis...",
      isComplete: true,
      timestamp: Date.now(),
    },
    {
      type: "complete",
      result: { answer: "Test complete", confidence: 0.95 },
      summary: "Successfully completed task",
      timestamp: Date.now(),
    },
  ],

  /**
   * Flow requiring human approval
   */
  withApproval: [
    {
      type: "agent_response",
      agent: "coder",
      content: "I will write code to solve this...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "approval_request",
      id: "approval-123",
      operation: "code_execution",
      params: { code: 'print("Hello, World!")' },
      context: "Execute Python code to test functionality",
      risk_level: "low",
      timestamp: Date.now(),
    },
    // After approval...
    {
      type: "tool_call",
      tool: "code_interpreter",
      args: { code: 'print("Hello, World!")' },
      result: { stdout: "Hello, World!\n", stderr: "", exit_code: 0 },
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "coder",
      content: "Code executed successfully.",
      isComplete: true,
      timestamp: Date.now(),
    },
    {
      type: "complete",
      result: { success: true, output: "Hello, World!\n" },
      timestamp: Date.now(),
    },
  ],

  /**
   * Flow with high-risk approval
   */
  highRiskApproval: [
    {
      type: "agent_response",
      agent: "coder",
      content: "This operation requires file system access...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "approval_request",
      id: "approval-456",
      operation: "file_write",
      params: {
        path: "/important/config.json",
        content: '{"setting": "value"}',
      },
      context: "Write configuration file with sensitive data",
      risk_level: "high",
      timestamp: Date.now(),
    },
  ],

  /**
   * Error scenario with recovery attempt
   */
  withError: [
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "Starting task...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "error",
      error: "API rate limit exceeded",
      details: "OpenAI API returned 429 status",
      recoverable: true,
      timestamp: Date.now(),
    },
    {
      type: "progress",
      step: "retry",
      progress: 0.3,
      message: "Retrying with backoff...",
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "Retry successful.",
      isComplete: true,
      timestamp: Date.now(),
    },
    {
      type: "complete",
      result: { success: true },
      timestamp: Date.now(),
    },
  ],

  /**
   * Fatal error scenario
   */
  fatalError: [
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "Starting complex task...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "error",
      error: "Configuration invalid",
      details: "Missing required API key",
      recoverable: false,
      timestamp: Date.now(),
    },
    {
      type: "complete",
      result: null,
      summary: "Task failed due to configuration error",
      timestamp: Date.now(),
    },
  ],

  /**
   * Multi-agent collaboration
   */
  collaboration: [
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "Breaking down the task...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "progress",
      step: "planning",
      progress: 0.1,
      message: "Creating plan",
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "researcher",
      content: "Gathering data...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "tool_call",
      tool: "web_search",
      args: { query: "research topic" },
      result: { results: [{ title: "Article 1", url: "https://example.com" }] },
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "analyst",
      content: "Analyzing findings...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "progress",
      step: "analysis",
      progress: 0.7,
      message: "Analyzing data",
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "coder",
      content: "Implementing solution...",
      isComplete: false,
      timestamp: Date.now(),
    },
    {
      type: "agent_response",
      agent: "orchestrator",
      content: "All tasks complete. Here is the final result...",
      isComplete: true,
      timestamp: Date.now(),
    },
    {
      type: "complete",
      result: {
        research: "summary",
        analysis: "insights",
        implementation: "code",
      },
      summary: "Multi-agent collaboration successful",
      timestamp: Date.now(),
    },
  ],
};

/**
 * Helper to simulate SSE scenario with delays
 */
export async function simulateSSEScenario(
  mockEventSource: MockEventSource,
  scenario: Array<Record<string, unknown>>,
  delayMs = 100
): Promise<void> {
  for (const event of scenario) {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    mockEventSource.simulateMessage(event as AnySSEEvent);
  }
}
