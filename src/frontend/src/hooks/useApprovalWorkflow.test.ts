import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  useApprovalWorkflow,
  type PendingApproval,
} from "./useApprovalWorkflow";
import { API_ENDPOINTS, buildApiUrl } from "../lib/api-config";

// Mock the API config
vi.mock("../lib/api-config", () => ({
  API_ENDPOINTS: {
    APPROVALS: "/v1/approvals",
    APPROVAL_RESPONSE: (id: string) => `/v1/approvals/${id}/respond`,
  },
  buildApiUrl: (url: string) => `http://localhost:8000${url}`,
}));

describe("useApprovalWorkflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should initialize with empty approvals", () => {
    const { result } = renderHook(() => useApprovalWorkflow());

    expect(result.current.pendingApprovals).toEqual([]);
    expect(result.current.approvalStatuses).toEqual({});
  });

  it("should handle approval requested event", () => {
    const { result } = renderHook(() => useApprovalWorkflow());

    const approval: PendingApproval = {
      id: "req-1",
      operation_type: "test_operation",
      description: "Test approval",
      details: {},
    };

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
    });

    expect(result.current.pendingApprovals).toHaveLength(1);
    expect(result.current.pendingApprovals[0].id).toBe("req-1");
    expect(result.current.approvalStatuses["req-1"]).toBe("pending");
  });

  it("should not duplicate approvals", () => {
    const { result } = renderHook(() => useApprovalWorkflow());

    const approval: PendingApproval = {
      id: "req-1",
      operation_type: "test_operation",
      description: "Test approval",
      details: {},
    };

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
    });

    expect(result.current.pendingApprovals).toHaveLength(1);
  });

  it("should handle approval responded event", () => {
    const { result } = renderHook(() => useApprovalWorkflow());

    const approval: PendingApproval = {
      id: "req-1",
      operation_type: "test_operation",
      description: "Test approval",
      details: {},
    };

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
    });

    expect(result.current.pendingApprovals).toHaveLength(1);

    act(() => {
      result.current.handleApprovalResponded({
        request_id: "req-1",
        response: {
          decision: "approve",
        },
      });
    });

    expect(result.current.pendingApprovals).toHaveLength(0);
    expect(result.current.approvalStatuses["req-1"]).toBe("completed");
  });

  it("should fetch approvals from API", async () => {
    const mockApprovals: PendingApproval[] = [
      {
        id: "req-1",
        operation_type: "test_operation",
        description: "Test approval 1",
        details: {},
      },
      {
        id: "req-2",
        operation_type: "test_operation",
        description: "Test approval 2",
        details: {},
      },
    ];

    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ approvals: mockApprovals }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useApprovalWorkflow());

    await act(async () => {
      await result.current.fetchApprovals();
    });

    await waitFor(() => {
      expect(result.current.pendingApprovals).toHaveLength(2);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      buildApiUrl(API_ENDPOINTS.APPROVALS),
    );
  });

  it("should handle fetch approvals error gracefully", async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useApprovalWorkflow());

    await act(async () => {
      await result.current.fetchApprovals();
    });

    // Should not throw, but approvals remain empty
    expect(result.current.pendingApprovals).toEqual([]);
  });

  it("should respond to approval with approve decision", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useApprovalWorkflow());

    const approval: PendingApproval = {
      id: "req-1",
      operation_type: "test_operation",
      description: "Test approval",
      details: {},
    };

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
    });

    await act(async () => {
      await result.current.respondToApproval("req-1", {
        decision: "approve",
      });
    });

    await waitFor(() => {
      expect(result.current.approvalStatuses["req-1"]).toBe("completed");
    });

    expect(result.current.pendingApprovals).toHaveLength(0);
    expect(global.fetch).toHaveBeenCalledWith(
      buildApiUrl(API_ENDPOINTS.APPROVAL_RESPONSE("req-1")),
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ decision: "approve" }),
      }),
    );
  });

  it("should handle approval response error", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Failed" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useApprovalWorkflow());

    const approval: PendingApproval = {
      id: "req-1",
      operation_type: "test_operation",
      description: "Test approval",
      details: {},
    };

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: approval,
      });
    });

    await act(async () => {
      try {
        await result.current.respondToApproval("req-1", {
          decision: "approve",
        });
      } catch {
        // Expected to throw
      }
    });

    await waitFor(() => {
      expect(result.current.approvalStatuses["req-1"]).toBe("error");
    });

    // Approval should still be pending on error
    expect(result.current.pendingApprovals).toHaveLength(1);
  });

  it("should clear all approvals", () => {
    const { result } = renderHook(() => useApprovalWorkflow());

    act(() => {
      result.current.handleApprovalRequested({
        request_id: "req-1",
        request: {
          id: "req-1",
          operation_type: "test_operation",
          description: "Test approval",
          details: {},
        },
      });
      result.current.handleApprovalRequested({
        request_id: "req-2",
        request: {
          id: "req-2",
          operation_type: "test_operation",
          description: "Test approval 2",
          details: {},
        },
      });
    });

    expect(result.current.pendingApprovals).toHaveLength(2);

    act(() => {
      result.current.clearApprovals();
    });

    expect(result.current.pendingApprovals).toHaveLength(0);
    expect(result.current.approvalStatuses).toEqual({});
  });
});
