import { useState } from "react";
import type { OrchestratorMessage } from "@/types/chat";
import { cn } from "@/lib/utils";
import { StructuredMessageContent } from "./StructuredMessageContent";

interface ChainOfThoughtProps {
  messages: OrchestratorMessage[];
}

/** Chain-of-thought component for displaying orchestrator messages */
export function ChainOfThought({ messages }: ChainOfThoughtProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  if (messages.length === 0) {
    return null;
  }

  // Group messages by kind
  const groupedMessages = messages.reduce(
    (acc, msg) => {
      const key = msg.kind || "default";
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(msg);
      return acc;
    },
    {} as Record<string, OrchestratorMessage[]>,
  );

  const toggleGroup = (key: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <div className="space-y-2">
      {Object.entries(groupedMessages).map(([kind, msgs]) => {
        const isExpanded = expandedGroups.has(kind);
        const kindLabel = getKindLabel(kind);

        return (
          <div
            key={kind}
            className="rounded-lg border border-border bg-muted/50 p-3"
          >
            <button
              onClick={() => toggleGroup(kind)}
              className="flex w-full items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">
                  {kindLabel}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({msgs.length} {msgs.length === 1 ? "message" : "messages"})
                </span>
              </div>
              <svg
                className={cn(
                  "h-4 w-4 transition-transform",
                  isExpanded && "rotate-180",
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {isExpanded && (
              <div className="mt-2 space-y-2 pl-2">
                {msgs.map((msg) => (
                  <div key={msg.id} className="rounded bg-background/50 p-2">
                    <StructuredMessageContent
                      content={msg.message}
                      isStreaming={false}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Get human-readable label for orchestrator message kind */
function getKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    default: "Thinking",
    task_ledger: "Task Plan",
    progress_ledger: "Progress Evaluation",
    facts: "Facts & Reasoning",
  };
  return labels[kind] || kind.charAt(0).toUpperCase() + kind.slice(1);
}
