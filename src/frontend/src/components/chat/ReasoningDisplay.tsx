import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ui/reasoning";
import type { ReasoningSection } from "@/types/chat";
import { Brain, Lightbulb } from "lucide-react";

interface ReasoningDisplayProps {
  /** Reasoning sections to display */
  sections?: ReasoningSection[];
  /** Raw reasoning content (for o1/o3 model reasoning tokens) */
  content?: string;
  /** Whether the reasoning is currently streaming */
  isStreaming?: boolean;
  /** Whether to start open by default */
  defaultOpen?: boolean;
  /** Maximum number of sections to display */
  maxSections?: number;
  /** Maximum content length before truncation */
  truncateLength?: number;
  /** Custom trigger text */
  triggerText?: string;
  /** Custom className */
  className?: string;
}

/**
 * ReasoningDisplay component wraps PromptKit Reasoning to display
 * model reasoning traces, explanations, and rationales.
 *
 * Supports two modes:
 * 1. Section-based: Display multiple ReasoningSection objects (orchestrator reasoning)
 * 2. Content-based: Display raw reasoning content (o1/o3 reasoning tokens)
 *
 * The component auto-closes when streaming completes (isStreaming changes to false).
 *
 * Usage:
 * ```tsx
 * // Section-based (orchestrator reasoning)
 * <ReasoningDisplay
 *   sections={reasoningSections}
 *   isStreaming={isCurrentlyStreaming}
 * />
 *
 * // Content-based (o1/o3 reasoning tokens)
 * <ReasoningDisplay
 *   content={reasoningContent}
 *   isStreaming={isCurrentlyStreaming}
 *   triggerText="Model reasoning"
 * />
 * ```
 */
export function ReasoningDisplay({
  sections = [],
  content,
  isStreaming = false,
  defaultOpen = false,
  maxSections = 6,
  truncateLength = 600,
  triggerText,
  className,
}: ReasoningDisplayProps) {
  // If raw content is provided, render single Reasoning component
  if (content && content.trim() !== "") {
    return (
      <Reasoning
        open={defaultOpen}
        isStreaming={isStreaming}
        className={className}
      >
        <ReasoningTrigger className="flex items-center gap-2">
          <Brain className="size-4" />
          <span className="font-medium">{triggerText || "View reasoning"}</span>
        </ReasoningTrigger>
        <ReasoningContent markdown className="mt-2">
          {truncateIfNeeded(content, truncateLength)}
        </ReasoningContent>
      </Reasoning>
    );
  }

  // Section-based display
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
          className={className}
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
