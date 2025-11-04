import {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
} from "@/components/ui/chain-of-thought";
import { Brain, Circle } from "lucide-react";
import type { ThoughtNode } from "@/types/chat";

interface ChainOfThoughtDisplayProps {
  thoughts: ThoughtNode[];
  isStreaming?: boolean;
  defaultOpen?: boolean;
  maxThoughts?: number;
  truncateLength?: number;
}

/**
 * ChainOfThoughtDisplay component wraps PromptKit ChainOfThought
 * to display sequential reasoning flow from orchestrator
 */
export function ChainOfThoughtDisplay({
  thoughts,
  isStreaming = false,
  defaultOpen = false,
  maxThoughts = 20,
  truncateLength = 280,
}: ChainOfThoughtDisplayProps) {
  if (thoughts.length === 0) {
    return null;
  }

  const limitedThoughts = thoughts.slice(0, maxThoughts);

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="size-5 text-primary" />
        <span className="font-medium text-foreground">Chain of Thought</span>
        <span className="text-xs text-muted-foreground">
          ({limitedThoughts.length}{" "}
          {limitedThoughts.length === 1 ? "thought" : "thoughts"})
        </span>
      </div>
      <ChainOfThought>
        {limitedThoughts.map((thought, index) => (
          <ChainOfThoughtStep
            key={thought.id}
            defaultOpen={
              defaultOpen ||
              (isStreaming && index === limitedThoughts.length - 1)
            }
          >
            <ChainOfThoughtTrigger
              leftIcon={
                <Circle
                  className={`size-3 ${
                    thought.type === "fact"
                      ? "fill-blue-500 text-blue-500"
                      : thought.type === "deduction"
                        ? "fill-amber-500 text-amber-500"
                        : "fill-green-500 text-green-500"
                  }`}
                />
              }
            >
              <span className="capitalize">{thought.type}</span>
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              <ChainOfThoughtItem>
                {truncateThought(thought.content, truncateLength)}
              </ChainOfThoughtItem>
            </ChainOfThoughtContent>
          </ChainOfThoughtStep>
        ))}
      </ChainOfThought>
    </div>
  );
}

function truncateThought(content: string, maxLength: number): string {
  if (content.length <= maxLength) {
    return content;
  }
  const slice = content.slice(0, maxLength);
  const lastBreak = Math.max(
    slice.lastIndexOf("\n\n"),
    slice.lastIndexOf(". "),
  );
  const endIndex = lastBreak > maxLength * 0.6 ? lastBreak + 1 : slice.length;
  return `${slice.slice(0, endIndex).trim()} …`;
}
