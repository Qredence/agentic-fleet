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
  maxSections?: number;
  truncateLength?: number;
}

/**
 * ReasoningDisplay component wraps PromptKit Reasoning to display
 * explanations, rationales, and reasoning from orchestrator messages
 */
export function ReasoningDisplay({
  sections,
  isStreaming = false,
  defaultOpen = false,
  maxSections = 6,
  truncateLength = 600,
}: ReasoningDisplayProps) {
  if (sections.length === 0) {
    return null;
  }

  const limitedSections = sections.slice(0, maxSections);

  return (
    <div className="space-y-3">
      {limitedSections.map((section, index) => (
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
            {truncateIfNeeded(section.content, truncateLength)}
          </ReasoningContent>
        </Reasoning>
      ))}
    </div>
  );
}

function truncateIfNeeded(content: string, maxLength: number): string {
  if (content.length <= maxLength) {
    return content;
  }
  const slice = content.slice(0, maxLength);
  const lastBreak = Math.max(
    slice.lastIndexOf("\n\n"),
    slice.lastIndexOf(". "),
  );
  const endIndex = lastBreak > maxLength * 0.6 ? lastBreak + 1 : slice.length;
  return `${slice.slice(0, endIndex).trim()}\n\n…`;
}
