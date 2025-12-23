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
 * Handles arrays, objects, and special fields with proper formatting.
 */
export function formatExtraDataMarkdown(data: Record<string, unknown>): string {
  const lines: string[] = [];

  // Format field name for display (convert snake_case to Title Case)
  const formatFieldName = (key: string): string => {
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined || value === "") continue;

    const displayName = formatFieldName(key);

    // Handle arrays - format as markdown list
    if (Array.isArray(value)) {
      if (value.length === 0) continue;

      // Special handling for certain fields
      if (key === "subtasks" || key === "assigned_to") {
        lines.push(`**${displayName}**:`);
        value.forEach((item, index) => {
          const itemStr =
            typeof item === "string" ? item.trim() : JSON.stringify(item);
          if (itemStr) {
            lines.push(`  ${index + 1}. ${itemStr}`);
          }
        });
      } else if (key === "capabilities") {
        // Format capabilities as comma-separated or list
        lines.push(
          `**${displayName}**: ${value.map((v) => String(v)).join(", ")}`,
        );
      } else {
        lines.push(`**${displayName}**:`);
        value.forEach((item) => {
          const itemStr =
            typeof item === "string" ? item.trim() : JSON.stringify(item);
          if (itemStr) {
            lines.push(`- ${itemStr}`);
          }
        });
      }
      lines.push(""); // Add spacing after list
      continue;
    }

    // Handle objects - format nested structure
    if (typeof value === "object") {
      const objStr = JSON.stringify(value, null, 2);
      lines.push(`**${displayName}**:`);
      lines.push("```json");
      lines.push(objStr);
      lines.push("```");
      lines.push(""); // Add spacing
      continue;
    }

    // Handle strings - preserve line breaks for reasoning
    if (typeof value === "string") {
      const trimmedValue = value.trim();
      if (!trimmedValue) continue;

      if (key === "reasoning") {
        // Preserve line breaks and formatting for reasoning
        lines.push(`**${displayName}**:`);
        lines.push(trimmedValue);
      } else {
        // Simple string values
        lines.push(`**${displayName}**: ${trimmedValue}`);
      }
      continue;
    }

    // Handle boolean values
    if (typeof value === "boolean") {
      lines.push(`**${displayName}**: ${value ? "Yes" : "No"}`);
      continue;
    }

    // Handle primitive values
    lines.push(`**${displayName}**: ${String(value)}`);
  }

  return lines.join("\n");
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
 * Reasoning steps are those with type "reasoning" (GPT-5 reasoning tokens).
 * All other steps, including orchestrator "thought" events, are trace steps.
 */
export function splitSteps(steps: ConversationStep[]): {
  reasoning: string;
  trace: ConversationStep[];
} {
  const reasoningParts: string[] = [];
  const trace: ConversationStep[] = [];

  for (const step of steps) {
    // Only GPT-5 reasoning tokens go to reasoning string
    // Orchestrator thoughts (analysis, routing, etc.) go to trace
    if (step.type === "reasoning") {
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
