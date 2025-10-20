import { memo } from "react";
import { Clock } from "lucide-react";
import { PendingApprovalCard } from "./agenticfleet-chatbot";
import type { ApprovalActionState, PendingApproval } from "@/lib/use-fastapi-chat";

interface PendingApprovalsProps {
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  onRespondToApproval: (requestId: string, approved: boolean) => () => void;
}

const PendingApprovals = memo(
  ({ pendingApprovals, approvalStatuses, onRespondToApproval }: PendingApprovalsProps) => (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 rounded-3xl border border-yellow-200/60 bg-yellow-100/20 p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-semibold text-yellow-800">
        <Clock size={16} aria-hidden="true" />
        <span>Pending approvals</span>
      </div>
      <div className="space-y-3">
        {pendingApprovals.map((approval) => (
          <PendingApprovalCard
            key={approval.requestId}
            approval={approval}
            status={approvalStatuses[approval.requestId]}
            onApprove={onRespondToApproval(approval.requestId, true)}
            onReject={onRespondToApproval(approval.requestId, false)}
          />
        ))}
      </div>
    </div>
  )
);

PendingApprovals.displayName = "PendingApprovals";

export default PendingApprovals;
