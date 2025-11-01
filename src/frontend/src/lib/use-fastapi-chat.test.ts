import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useFastAPIChat } from "./use-fastapi-chat";
import { API_ENDPOINTS, buildApiUrl } from "./api-config";

// Mock the composed hooks
vi.mock("../hooks/useMessageState", () => ({
  useMessageState: vi.fn(() => ({
    messages: [],
    setMessages: vi.fn(),
    addMessage: vi.fn(),
    clearMessages: vi.fn(),
    isStreaming: vi.fn(() => false),
    startStreamingMessage: vi.fn(),
    appendDelta: vi.fn(),
    finishStreaming: vi.fn(),
    resetStreaming: vi.fn(),
  })),
}));

vi.mock("../hooks/useApprovalWorkflow", () => ({
  useApprovalWorkflow: vi.fn(() => ({
    pendingApprovals: [],
    approvalStatuses: {},
    handleApprovalRequested: vi.fn(),
    handleApprovalResponded: vi.fn(),
    respondToApproval: vi.fn(),
    fetchApprovals: vi.fn(),
    clearApprovals: vi.fn(),
  })),
}));

vi.mock("../hooks/useConversationHistory", () => ({
  useConversationHistory: vi.fn(() => ({
    loadHistory: vi.fn(() => Promise.resolve([])),
  })),
}));

// Mock the API config
vi.mock("./api-config", () => ({
  API_ENDPOINTS: {
    HEALTH: "/v1/system/health",
    CONVERSATIONS: "/v1/conversations",
    RESPONSES: "/v1/responses",
    APPROVALS: "/v1/approvals",
    APPROVAL_RESPONSE: (id: string) => `/v1/approvals/${id}/respond`,
    CONVERSATION_MESSAGES: (id: string) => `/v1/conversations/${id}`,
  },
  buildApiUrl: (url: string) => `http://localhost:8000${url}`,
}));

const createJsonResponse = (body: unknown, init?: ResponseInit): Response =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });

const createSSEStreamResponse = (
  payloads: string[],
  options: { delayMs?: number } = {},
): Response => {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      for (const payload of payloads) {
        controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
        if (options.delayMs) {
          await new Promise((resolve) => setTimeout(resolve, options.delayMs));
        }
      }
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
};

const getFetchMock = (): vi.Mock => global.fetch as unknown as vi.Mock;

vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);

describe("useFastAPIChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>(
      async () => createJsonResponse({ status: "ok" }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should initialize with default values", () => {
    const { result } = renderHook(() => useFastAPIChat());

    expect(result.current.messages).toEqual([]);
    expect(result.current.input).toBe("");
    expect(result.current.status).toBe("ready");
    expect(result.current.error).toBeNull();
    expect(result.current.pendingApprovals).toEqual([]);
    expect(result.current.connectionStatus).toBe("connecting");
  });

  it("should initialize with provided conversation ID", () => {
    const { result } = renderHook(() =>
      useFastAPIChat({ conversationId: "conv-123" }),
    );

    expect(result.current.conversationId).toBe("conv-123");
  });

  it("should update input value", () => {
    const { result } = renderHook(() => useFastAPIChat());

    act(() => {
      result.current.setInput("Hello world");
    });

    expect(result.current.input).toBe("Hello world");
  });

  it("should check health successfully", async () => {
    const { result } = renderHook(() => useFastAPIChat());

    await act(async () => {
      await result.current.checkHealth();
    });

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe("connected");
    });

    expect(getFetchMock()).toHaveBeenCalledWith(
      buildApiUrl(API_ENDPOINTS.HEALTH),
      expect.objectContaining({
        method: "GET",
      }),
    );
  });

  it("should handle health check failure", async () => {
    const fetchMock = getFetchMock();
    fetchMock.mockImplementation(() =>
      Promise.reject(new Error("Network error")),
    );

    const { result } = renderHook(() => useFastAPIChat());

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe("disconnected");
    });
  });

  it("should create conversation if none exists when sending message", async () => {
    const mockMessageState = {
      messages: [],
      setMessages: vi.fn(),
      addMessage: vi.fn(),
      clearMessages: vi.fn(),
      isStreaming: vi.fn(() => false),
      startStreamingMessage: vi.fn(),
      appendDelta: vi.fn(),
      finishStreaming: vi.fn(),
      resetStreaming: vi.fn(),
    };

    vi.mocked(
      await import("../hooks/useMessageState"),
    ).useMessageState.mockReturnValue(mockMessageState as never);

    const fetchMock = getFetchMock();
    fetchMock
      .mockImplementationOnce(async () => createJsonResponse({ status: "ok" })) // health check
      .mockImplementationOnce(async () =>
        createJsonResponse({ id: "conv-456" }),
      )
      .mockImplementationOnce(async () =>
        createSSEStreamResponse([
          JSON.stringify({
            type: "response.completed",
            message_id: "msg-1",
            response: { conversation_id: "conv-456" },
          }),
        ]),
      );

    const { result } = renderHook(() => useFastAPIChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        buildApiUrl(API_ENDPOINTS.CONVERSATIONS),
        expect.objectContaining({
          method: "POST",
        }),
      );
    });
  });

  it("should not send message if already streaming", async () => {
    const fetchMock = getFetchMock();
    let resolveResponse: (() => void) | undefined;
    let responseInFlight = false;
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveResponse = () => {
        responseInFlight = false;
        resolve(
          createSSEStreamResponse([
            JSON.stringify({
              type: "response.completed",
              message_id: "msg-789",
              response: { conversation_id: "conv-789" },
            }),
          ]),
        );
      };
    });

    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.endsWith("/v1/system/health")) {
        return createJsonResponse({ status: "ok" });
      }

      if (url.endsWith("/v1/conversations")) {
        return createJsonResponse({ id: "conv-789" });
      }

      if (url.endsWith("/v1/responses")) {
        if (responseInFlight) {
          throw new Error("Duplicate response fetch attempted");
        }
        responseInFlight = true;
        return pendingResponse;
      }

      return createJsonResponse({ status: "ok" });
    });

    const { result } = renderHook(() => useFastAPIChat());

    let firstSendPromise: Promise<void> | undefined;
    await act(async () => {
      firstSendPromise = result.current.sendMessage("First message");
      firstSendPromise ??= Promise.resolve();
    });

    let secondSendPromise: Promise<void> | undefined;
    await act(async () => {
      secondSendPromise = result.current.sendMessage("Second message");
    });
    secondSendPromise ??= Promise.resolve();

    resolveResponse?.();

    await act(async () => {
      await firstSendPromise;
      await secondSendPromise;
    });
  });

  it("should handle send message error", async () => {
    const fetchMock = getFetchMock();
    fetchMock
      .mockImplementationOnce(async () => createJsonResponse({ status: "ok" })) // health check
      .mockImplementation(() => Promise.reject(new Error("Network error")));

    const { result } = renderHook(() => useFastAPIChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    await waitFor(() => {
      expect(result.current.status).toBe("error");
      expect(result.current.error).toBeTruthy();
    });
  });

  it("should handle refresh approvals", async () => {
    const mockApprovalWorkflow = {
      pendingApprovals: [],
      approvalStatuses: {},
      handleApprovalRequested: vi.fn(),
      handleApprovalResponded: vi.fn(),
      respondToApproval: vi.fn(),
      fetchApprovals: vi.fn(() => Promise.resolve()),
      clearApprovals: vi.fn(),
    };

    vi.mocked(
      await import("../hooks/useApprovalWorkflow"),
    ).useApprovalWorkflow.mockReturnValue(mockApprovalWorkflow as never);

    const { result } = renderHook(() => useFastAPIChat());

    await act(async () => {
      await result.current.refreshApprovals();
    });

    expect(mockApprovalWorkflow.fetchApprovals).toHaveBeenCalled();
  });

  it("should respond to approval", async () => {
    const mockApprovalWorkflow = {
      pendingApprovals: [],
      approvalStatuses: {},
      handleApprovalRequested: vi.fn(),
      handleApprovalResponded: vi.fn(),
      respondToApproval: vi.fn(() => Promise.resolve()),
      fetchApprovals: vi.fn(),
      clearApprovals: vi.fn(),
    };

    vi.mocked(
      await import("../hooks/useApprovalWorkflow"),
    ).useApprovalWorkflow.mockReturnValue(mockApprovalWorkflow as never);

    const { result } = renderHook(() => useFastAPIChat());

    await act(async () => {
      await result.current.respondToApproval("req-1", {
        decision: "approve",
      });
    });

    expect(mockApprovalWorkflow.respondToApproval).toHaveBeenCalledWith(
      "req-1",
      {
        decision: "approve",
      },
    );
  });
});
