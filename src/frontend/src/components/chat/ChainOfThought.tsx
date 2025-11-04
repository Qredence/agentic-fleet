import type { OrchestratorMessage } from "@/types/chat";
import { SystemMessage } from "@/components/ui/system-message";
import { StructuredMessageContent } from "./StructuredMessageContent";

interface ChainOfThoughtProps {
  messages: OrchestratorMessage[];
}

const KIND_METADATA: Record<
  string,
  {
    title: string;
    variant: "info" | "warning" | "success" | "action" | "error";
  }
> = {
  task_ledger: { title: "Task Plan", variant: "action" },
  progress_ledger: { title: "Progress Evaluation", variant: "warning" },
  facts: { title: "Facts & Reasoning", variant: "info" },
  default: { title: "Manager Update", variant: "info" },
};

/** Renders orchestrator / manager messages in dedicated system cards. */
export function ChainOfThought({ messages }: ChainOfThoughtProps) {
  if (!messages.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      {messages.map((message) => {
        const meta =
          KIND_METADATA[message.kind || "default"] ?? KIND_METADATA.default;
        const timestamp =
          message.timestamp !== undefined
            ? new Date(message.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })
            : undefined;

        return (
          <SystemMessage
            key={message.id}
            title={timestamp ? `${meta.title} · ${timestamp}` : meta.title}
            variant={meta.variant}
            size="md"
            className="shadow-sm"
          >
            <StructuredMessageContent
              content={message.message}
              kind={message.kind}
              isStreaming={false}
            />
          </SystemMessage>
        );
      })}
    </div>
  );
}
