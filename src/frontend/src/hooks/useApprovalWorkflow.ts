/**
 * useApprovalWorkflow Hook
 *
 * Manages Human-in-the-loop approval requests
 * Now uses Zustand store for state management
 */

import { useCallback } from "react";
import { API_ENDPOINTS, buildApiUrl } from "../lib/api-config";
import { useApprovalStore } from "../stores/approvalStore";

export interface PendingApproval {
  id: string;
  operation_type: string;
  description: string;
  details: Record<string, unknown>;
  timeout_seconds?: number;
  requested_at?: string;
}

export type ApprovalActionState =
  | "pending"
  | "approving"
  | "rejecting"
  | "modifying"
  | "completed"
  | "error";

export interface ApprovalResponsePayload {
  decision: "approve" | "reject" | "modify";
  modified_details?: Record<string, unknown>;
  reason?: string;
}

export interface UseApprovalWorkflowReturn {
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  handleApprovalRequested: (event: {
    request_id: string;
    request: PendingApproval;
  }) => void;
  handleApprovalResponded: (event: {
    request_id: string;
    response: ApprovalResponsePayload;
  }) => void;
  respondToApproval: (
    requestId: string,
    payload: ApprovalResponsePayload,
  ) => Promise<void>;
  fetchApprovals: () => Promise<void>;
  clearApprovals: () => void;
}

export function useApprovalWorkflow(): UseApprovalWorkflowReturn {
  const {
    pendingApprovals,
    approvalStatuses,
    addApproval,
    removeApproval,
    updateStatus,
    clearAll,
    setApprovals,
  } = useApprovalStore();

  const handleApprovalRequested = useCallback(
    (event: { request_id: string; request: PendingApproval }) => {
      addApproval({ ...event.request, id: event.request_id });
    },
    [addApproval],
  );

  const handleApprovalResponded = useCallback(
    (event: { request_id: string; response: ApprovalResponsePayload }) => {
      removeApproval(event.request_id);
    },
    [removeApproval],
  );

  const respondToApproval = useCallback(
    async (requestId: string, payload: ApprovalResponsePayload) => {
      const actionState: ApprovalActionState =
        payload.decision === "approve"
          ? "approving"
          : payload.decision === "reject"
            ? "rejecting"
            : "modifying";

      updateStatus(requestId, actionState);

      try {
        const response = await fetch(
          buildApiUrl(API_ENDPOINTS.APPROVAL_RESPONSE(requestId)),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          },
        );

        if (!response.ok) {
          throw new Error(
            `Failed to respond to approval: ${response.status} ${response.statusText}`,
          );
        }

        removeApproval(requestId);
      } catch (error) {
        console.error("Error responding to approval:", error);
        updateStatus(requestId, "error");
        throw error;
      }
    },
    [updateStatus, removeApproval],
  );

  const fetchApprovals = useCallback(async () => {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.APPROVALS));
      if (!response.ok) {
        throw new Error(`Failed to fetch approvals: ${response.status}`);
      }

      const data = (await response.json()) as { approvals: PendingApproval[] };
      setApprovals(data.approvals || []);
    } catch (error) {
      console.error("Error fetching approvals:", error);
    }
  }, [setApprovals]);

  const clearApprovals = useCallback(() => {
    clearAll();
  }, [clearAll]);

  return {
    pendingApprovals,
    approvalStatuses,
    handleApprovalRequested,
    handleApprovalResponded,
    respondToApproval,
    fetchApprovals,
    clearApprovals,
  };
}
