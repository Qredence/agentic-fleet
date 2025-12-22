import type { ConversationStep } from "@/api/types";

/**
 * Parse a response string, attempting JSON parsing first, falling back to the string itself.
 */
export function parseResponse(value: string): unknown {
  if (!value.trim()) return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

/**
 * Safely coerce a value to a string.
 */
export function coerceString(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined;
  if (typeof value === "string") return value;
  return String(value);
}

/**
 * Format an object as markdown for display.
 */
export function formatExtraDataMarkdown(data: Record<string, unknown>): string {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) continue;
    const formattedValue =
      typeof value === "string"
        ? value
        : typeof value === "object"
          ? JSON.stringify(value, null, 2)
          : String(value);
    lines.push(`**${key}**: ${formattedValue}`);
  }
  return lines.join("\n\n");
}

/**
 * Format a timestamp as a relative time string.
 */
export function formatStepTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffSec < 60) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;

    // Format as date if older than 24 hours
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

/**
 * Get a label for a step based on its type and kind.
 */
export function getStepLabel(step: ConversationStep): {
  label: string;
  category?: string;
} {
  const type = step.type;
  const kind = step.kind || step.category;

  // Use kind if available, otherwise use type
  const label = kind || type || "unknown";

  return {
    label,
    category: step.category,
  };
}

/**
 * Split steps into reasoning steps and trace steps.
 * Reasoning steps are those with type "reasoning" or "thought".
 * All other steps are trace steps.
 */
export function splitSteps(steps: ConversationStep[]): {
  reasoning: string;
  trace: ConversationStep[];
} {
  const reasoningParts: string[] = [];
  const trace: ConversationStep[] = [];

  for (const step of steps) {
    if (step.type === "reasoning" || step.type === "thought") {
      if (step.content) {
        reasoningParts.push(step.content);
      }
    } else {
      trace.push(step);
    }
  }

  return {
    reasoning: reasoningParts.join("\n\n"),
    trace,
  };
}
