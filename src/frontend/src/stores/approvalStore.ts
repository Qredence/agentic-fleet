import { create } from "zustand";
import type {
  ApprovalActionState,
  PendingApproval,
} from "../hooks/useApprovalWorkflow";

interface ApprovalStore {
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  addApproval: (approval: PendingApproval) => void;
  removeApproval: (requestId: string) => void;
  updateStatus: (requestId: string, status: ApprovalActionState) => void;
  clearAll: () => void;
  setApprovals: (approvals: PendingApproval[]) => void;
}

export const useApprovalStore = create<ApprovalStore>((set) => ({
  pendingApprovals: [],
  approvalStatuses: {},

  addApproval: (approval) =>
    set((state) => {
      const exists = state.pendingApprovals.some((a) => a.id === approval.id);
      if (exists) return state;

      return {
        pendingApprovals: [...state.pendingApprovals, approval],
        approvalStatuses: {
          ...state.approvalStatuses,
          [approval.id]: "pending",
        },
      };
    }),

  removeApproval: (requestId) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter(
        (a) => a.id !== requestId,
      ),
      approvalStatuses: {
        ...state.approvalStatuses,
        [requestId]: "completed",
      },
    })),

  updateStatus: (requestId, status) =>
    set((state) => ({
      approvalStatuses: {
        ...state.approvalStatuses,
        [requestId]: status,
      },
    })),

  clearAll: () =>
    set({
      pendingApprovals: [],
      approvalStatuses: {},
    }),

  setApprovals: (approvals) =>
    set({
      pendingApprovals: approvals,
      approvalStatuses: approvals.reduce(
        (acc, approval) => {
          acc[approval.id] = "pending";
          return acc;
        },
        {} as Record<string, ApprovalActionState>,
      ),
    }),
}));
