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
}

/**
 * ChainOfThoughtDisplay component wraps PromptKit ChainOfThought
 * to display sequential reasoning flow from orchestrator
 */
export function ChainOfThoughtDisplay({
  thoughts,
  isStreaming = false,
  defaultOpen = false,
}: ChainOfThoughtDisplayProps) {
  if (thoughts.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="size-5 text-primary" />
        <span className="font-medium text-foreground">Chain of Thought</span>
        <span className="text-xs text-muted-foreground">
          ({thoughts.length} {thoughts.length === 1 ? "thought" : "thoughts"})
        </span>
      </div>
      <ChainOfThought>
        {thoughts.map((thought, index) => (
          <ChainOfThoughtStep
            key={thought.id}
            defaultOpen={
              defaultOpen || (isStreaming && index === thoughts.length - 1)
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
              <ChainOfThoughtItem>{thought.content}</ChainOfThoughtItem>
            </ChainOfThoughtContent>
          </ChainOfThoughtStep>
        ))}
      </ChainOfThought>
    </div>
  );
}
