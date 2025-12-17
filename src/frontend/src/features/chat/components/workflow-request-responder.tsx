import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { parseResponse } from "./utils";
import { useState } from "react";

export type WorkflowRequestResponderProps = {
  requestId: string;
  requestType?: string;
  onSubmit: (requestId: string, payload: unknown) => void;
  isLoading?: boolean;
};

export function WorkflowRequestResponder({
  requestId,
  requestType,
  onSubmit,
  isLoading = false,
}: WorkflowRequestResponderProps) {
  const [value, setValue] = useState("");

  const loweredType = (requestType || "").toLowerCase();
  const isApproval = loweredType.includes("approval");

  const submit = (payload: unknown) => {
    onSubmit(requestId, payload);
  };

  return (
    <div className="mt-2 rounded-md border border-border bg-muted/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {requestType
            ? `Type: ${requestType}`
            : "Workflow is waiting for a response"}
        </div>
        <div className="text-xs text-muted-foreground">
          request_id: {requestId}
        </div>
      </div>

      {isApproval ? (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => submit({ approved: true })}
            disabled={isLoading}
          >
            Approve
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => submit({ approved: false })}
            disabled={isLoading}
          >
            Deny
          </Button>
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={
            isApproval
              ? 'Optional: provide JSON payload (e.g. {"approved": true}) or a note'
              : "Enter a response (plain text or JSON)"
          }
          className="min-h-20"
        />
        <div className="flex items-center justify-end">
          <Button
            size="sm"
            onClick={() => submit(parseResponse(value))}
            disabled={isLoading || !value.trim()}
          >
            Send response
          </Button>
        </div>
      </div>
    </div>
  );
}
