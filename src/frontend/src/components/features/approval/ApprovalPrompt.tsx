import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/shadcn/badge";
import { Button } from "@/components/ui/shadcn/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/shadcn/card";
import { Label } from "@/components/ui/shadcn/label";
import { Separator } from "@/components/ui/shadcn/separator";
import { Textarea } from "@/components/ui/shadcn/textarea";
import type { ApprovalActionState, PendingApproval, RiskLevel } from "@/lib/types";
import {
  AlertTriangle,
  Check,
  FileEdit,
  Info,
  MinusCircle,
  Shield,
} from "lucide-react";
import { toast } from "sonner";

interface ApprovalPromptProps {
  approval: PendingApproval;
  status: ApprovalActionState;
  onApprove: (options?: {
    modifiedCode?: string;
    modifiedParams?: Record<string, unknown>;
    reason?: string;
  }) => void;
  onReject: (reason: string) => void;
}

export function ApprovalPrompt({ approval, status, onApprove, onReject }: ApprovalPromptProps) {
  const {
    requestId,
    operation,
    description,
    details: approvalDetails,
    riskLevel = "medium",
  } = approval;

  const functionCall = useMemo(() => {
    const details = approvalDetails ?? {};
    const raw =
      (details?.function_call as
        | { id?: string; name?: string; arguments?: Record<string, unknown> }
        | undefined) ??
      (details?.tool_call as
        | { id?: string; name?: string; arguments?: Record<string, unknown> }
        | undefined);
    if (!raw) {
      return undefined;
    }
    return {
      id: typeof raw.id === "string" ? raw.id : requestId,
      name:
        typeof raw.name === "string"
          ? raw.name
          : operation ?? "Agent Operation",
      arguments: (raw.arguments ?? {}) as Record<string, unknown>,
    };
  }, [approvalDetails, operation, requestId]);

  const baseDetails = useMemo(() => {
    const details = approvalDetails ?? {};
    if (functionCall?.arguments) {
      return functionCall.arguments;
    }
    if (typeof details.parameters === "object" && details.parameters !== null) {
      return details.parameters as Record<string, unknown>;
    }
    return details as Record<string, unknown>;
  }, [approvalDetails, functionCall]);

  const defaultCode = useMemo(() => {
    const details = approvalDetails ?? {};
    if (typeof details.code === "string") {
      return details.code;
    }
    if (functionCall?.arguments?.code && typeof functionCall.arguments.code === "string") {
      return functionCall.arguments.code as string;
    }
    return null;
  }, [approvalDetails, functionCall]);

  const displayContext = useMemo(() => {
    const details = approvalDetails ?? {};
    if (typeof details.context === "string") {
      return details.context;
    }
    return description;
  }, [approvalDetails, description]);
  const isSubmitting = status.status === "submitting";
  const hasError = status.status === "error";

  const initialCode = useMemo(() => {
    if (typeof defaultCode === "string" && defaultCode.trim().length > 0) {
      return defaultCode;
    }
    const argCode = functionCall?.arguments?.code;
    return typeof argCode === "string" ? argCode : "";
  }, [defaultCode, functionCall]);

  const [editedCode, setEditedCode] = useState(initialCode);
  const [isModifyingParams, setIsModifyingParams] = useState(false);
  const [editedParams, setEditedParams] = useState(() => {
    const params = functionCall?.arguments || baseDetails || {};
    return JSON.stringify(params, null, 2);
  });
  const [reason, setReason] = useState("");
  const [showValidation, setShowValidation] = useState(false);

  const getRiskBadge = () => {
    const riskConfig = {
      low: { color: "default", icon: Info, label: "LOW RISK" },
      medium: { color: "secondary", icon: AlertTriangle, label: "MEDIUM RISK" },
      high: { color: "destructive", icon: Shield, label: "HIGH RISK" },
    };
    const config = riskConfig[riskLevel];
    const Icon = config.icon;

    return (
      <Badge
        variant={config.color as "default" | "secondary" | "destructive"}
        className="gap-1 text-xs"
      >
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const handleReject = () => {
    if (!reason.trim()) {
      setShowValidation(true);
      return;
    }
    onReject(reason.trim());
  };

  const handleApprove = () => {
    const payload: {
      modifiedCode?: string;
      modifiedParams?: Record<string, unknown>;
      reason?: string;
    } = {};

    // Handle modified code
    if (editedCode && editedCode !== initialCode) {
      payload.modifiedCode = editedCode;
    }

    // Handle modified params
    if (isModifyingParams) {
      try {
        const parsed = JSON.parse(editedParams);
        payload.modifiedParams = parsed;
      } catch (err) {
        const errorMsg =
          err instanceof Error
            ? `Invalid JSON in modified parameters: ${err.message}`
            : "Invalid JSON in modified parameters";
        toast.error(errorMsg);
        return;
      }
    }

    if (reason.trim()) {
      payload.reason = reason.trim();
    }

    onApprove(Object.keys(payload).length ? payload : undefined);
  };

  const handleModifyToggle = () => {
    setIsModifyingParams(!isModifyingParams);
  };

  const argumentDetails = baseDetails || {};

  return (
    <Card className="border-amber-500/50 bg-amber-50/10 dark:bg-amber-950/10">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <CardTitle className="text-base">Approval Required</CardTitle>
          {getRiskBadge()}
        </div>
        <CardDescription className="text-xs">
          The agent is requesting permission to execute an operation
        </CardDescription>
      </CardHeader>

      <CardContent className="pb-3 space-y-3">
        <div className="space-y-3">
          <div className="bg-muted/50 rounded-md p-3 text-xs font-mono space-y-2">
            <div>
              <div className="text-muted-foreground mb-1">Request ID:</div>
              <div className="text-foreground break-all">{requestId}</div>
            </div>

            {(operation || functionCall?.name) && (
              <div>
                <div className="text-muted-foreground mb-1">Operation:</div>
                <div className="text-foreground break-words">
                  {operation || functionCall?.name}
                </div>
              </div>
            )}

            {displayContext && (
              <div>
                <div className="text-muted-foreground mb-1">Context:</div>
                <div className="text-foreground break-words whitespace-pre-wrap">
                  {displayContext}
                </div>
              </div>
            )}

            {Object.keys(argumentDetails).length > 0 && (
              <div>
                <Separator className="my-2" />
                <div className="flex items-center justify-between mb-1">
                  <div className="text-muted-foreground">Parameters:</div>
                  {!isModifyingParams && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={handleModifyToggle}
                    >
                      <FileEdit className="h-3 w-3 mr-1" />
                      Modify
                    </Button>
                  )}
                </div>
                {isModifyingParams ? (
                  <div className="space-y-2">
                    <Textarea
                      value={editedParams}
                      onChange={(e) => setEditedParams(e.target.value)}
                      className="font-mono text-xs min-h-[120px]"
                      spellCheck={false}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={handleModifyToggle}
                    >
                      Cancel Modifications
                    </Button>
                  </div>
                ) : (
                  <pre className="text-foreground whitespace-pre-wrap break-all max-h-40 overflow-auto">
                    {JSON.stringify(argumentDetails, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {initialCode && (
              <div className="space-y-2">
                <Separator className="my-2" />
                <div className="flex items-center gap-2">
                  <FileEdit className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">
                    Review &amp; Modify Code
                  </span>
                </div>
                <Textarea
                  value={editedCode}
                  onChange={(event) => setEditedCode(event.target.value)}
                  className="font-mono text-xs min-h-[140px]"
                  spellCheck={false}
                />
              </div>
            )}
          </div>
        </div>

        {hasError && (
          <div className="text-xs text-destructive bg-destructive/10 rounded-md p-2">
            <span className="font-medium">Error: </span>
            {status.error}
          </div>
        )}

        <div className="space-y-2">
          <Label
            htmlFor={`approval-reason-${requestId}`}
            className="text-xs text-muted-foreground"
          >
            Notes / Reason (required to reject)
          </Label>
          <Textarea
            id={`approval-reason-${requestId}`}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              setShowValidation(false);
            }}
            placeholder="Add optional context for your decision"
            className="text-sm"
          />
          {showValidation && !reason.trim() && (
            <p className="text-xs text-destructive flex items-center gap-1">
              <MinusCircle className="h-3 w-3" /> Please provide a reason to
              reject this request.
            </p>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex gap-2">
        <Button
          onClick={handleReject}
          disabled={isSubmitting}
          variant="outline"
          size="sm"
          className="flex-1"
        >
          <MinusCircle className="h-4 w-4 mr-1" />
          {isSubmitting ? "Submitting..." : "Reject"}
        </Button>
        <Button
          onClick={handleApprove}
          disabled={isSubmitting}
          variant="default"
          size="sm"
          className="flex-1 bg-green-600 hover:bg-green-700"
        >
          <Check className="h-4 w-4 mr-1" />
          {isSubmitting ? "Submitting..." : "Approve"}
        </Button>
      </CardFooter>
    </Card>
  );
}
