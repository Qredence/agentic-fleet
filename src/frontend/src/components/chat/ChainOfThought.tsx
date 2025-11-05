import {
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThought as ChainOfThoughtUI,
} from "@/components/ui/chain-of-thought";
import type { OrchestratorMessage } from "@/types/chat";
import { Clock, Info, Lightbulb, ListChecks } from "lucide-react";
import { StructuredMessageContent } from "./StructuredMessageContent";

interface ChainOfThoughtProps {
  messages: OrchestratorMessage[];
}

const KIND_METADATA: Record<
  string,
  {
    title: string;
    icon: React.ReactNode;
  }
> = {
  task_ledger: { title: "Task Plan", icon: <ListChecks className="size-4" /> },
  progress_ledger: {
    title: "Progress Evaluation",
    icon: <Clock className="size-4" />,
  },
  facts: { title: "Facts & Reasoning", icon: <Lightbulb className="size-4" /> },
  default: { title: "Manager Update", icon: <Info className="size-4" /> },
};

/** Renders orchestrator / manager messages using Prompt Kit ChainOfThought. */
export function ChainOfThought({ messages }: ChainOfThoughtProps) {
  if (!messages.length) {
    return null;
  }

  return (
    <ChainOfThoughtUI className="rounded-lg border border-border bg-card p-4">
      {messages.map((message, index) => {
        const meta =
          KIND_METADATA[message.kind || "default"] ?? KIND_METADATA.default;
        const timestamp =
          message.timestamp !== undefined
            ? new Date(message.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
            : undefined;

        return (
          <ChainOfThoughtStep
            key={message.id}
            defaultOpen={index === messages.length - 1}
          >
            <ChainOfThoughtTrigger leftIcon={meta.icon}>
              <span className="font-medium">{meta.title}</span>
              {timestamp && (
                <span className="ml-2 text-xs text-muted-foreground">
                  {timestamp}
                </span>
              )}
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              <ChainOfThoughtItem>
                <StructuredMessageContent
                  content={message.message}
                  kind={message.kind}
                  isStreaming={false}
                  className="text-sm"
                />
              </ChainOfThoughtItem>
            </ChainOfThoughtContent>
          </ChainOfThoughtStep>
        );
      })}
    </ChainOfThoughtUI>
  );
}
