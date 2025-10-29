import { apiRequest } from "./client";
import type { ApprovalDecisionPayload, ApprovalRecord } from "../types";

export const listApprovals = () => apiRequest<ApprovalRecord[]>("/v1/approvals");

export const submitApprovalDecision = (requestId: string, payload: ApprovalDecisionPayload) =>
  apiRequest(`/v1/approvals/${requestId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
