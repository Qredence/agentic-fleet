import type { Message as ChatMessage } from "@/api/types";
import { ChainOfThoughtTrace } from "@/features/workflow";
import type { ChainOfThoughtTraceProps } from "@/features/workflow/components/chain-of-thought";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export type TracePanelProps = {
  message: ChatMessage | null;
  isStreaming?: ChainOfThoughtTraceProps["isStreaming"];
} & Omit<ChainOfThoughtTraceProps, "message" | "isStreaming">;

export function TracePanel({
  message,
  isLoading,
  isStreaming,
  showRawReasoning,
  onWorkflowResponse,
}: TracePanelProps) {
  const streaming = isStreaming || isLoading;

  // Status label logic
  const statusLabel = streaming
    ? "Streaming"
    : message?.steps?.length
      ? "Complete"
      : "Idle";

  // Neutral badge variants: only streaming gets background
  const statusVariant = streaming ? "secondary" : "outline";

  return (
    <Card className="h-full border-0 bg-transparent shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-foreground">
            Chain of Thought
          </CardTitle>
          <Badge
            variant={statusVariant}
            className="text-xs font-mono text-muted-foreground"
          >
            {statusLabel}
          </Badge>
        </div>
      </CardHeader>

      {message ? (
        <CardContent className="flex-1 overflow-auto p-0">
          <ChainOfThoughtTrace
            message={message}
            isStreaming={streaming}
            isLoading={isLoading}
            showRawReasoning={showRawReasoning}
            onWorkflowResponse={onWorkflowResponse}
          />
        </CardContent>
      ) : (
        <CardContent className="flex-1 overflow-auto p-0">
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              No workflow events yet.
            </p>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
