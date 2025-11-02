import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "@/components/ui/reasoning";
import { Lightbulb } from "lucide-react";
import type { ReasoningSection } from "@/types/chat";

interface ReasoningDisplayProps {
  sections: ReasoningSection[];
  isStreaming?: boolean;
  defaultOpen?: boolean;
}

/**
 * ReasoningDisplay component wraps PromptKit Reasoning to display
 * explanations, rationales, and reasoning from orchestrator messages
 */
export function ReasoningDisplay({
  sections,
  isStreaming = false,
  defaultOpen = false,
}: ReasoningDisplayProps) {
  if (sections.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {sections.map((section, index) => (
        <Reasoning
          key={`reasoning-${index}`}
          open={defaultOpen || isStreaming}
          isStreaming={isStreaming}
        >
          <ReasoningTrigger className="flex items-center gap-2">
            <Lightbulb className="size-4" />
            <span className="font-medium capitalize">{section.title}</span>
          </ReasoningTrigger>
          <ReasoningContent markdown className="mt-2">
            {section.content}
          </ReasoningContent>
        </Reasoning>
      ))}
    </div>
  );
}
