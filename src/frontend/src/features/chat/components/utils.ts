import type { ConversationStep } from "@/api/types";

export function formatStepTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function getStepLabel(step: ConversationStep): { label: string } {
  const type = step.type;
  if (type === "error") return { label: "Error" };
  if (type === "analysis") return { label: "Analysis" };
  if (type === "routing") return { label: "Routing" };
  if (type === "quality") return { label: "Quality" };
  if (type === "progress") return { label: "Progress" };
  if (type === "request") return { label: "Request" };
  if (type === "tool_call") return { label: "Tool" };
  if (type === "handoff") return { label: "Handoff" };
  if (type === "agent_start") return { label: "Agent started" };
  if (type === "agent_complete") return { label: "Agent complete" };
  if (type === "agent_output") return { label: "Output" };
  if (type === "agent_thought") return { label: "Thought" };
  if (type === "reasoning") return { label: "Reasoning" };
  if (type === "status") return { label: "Status" };
  return { label: "Event" };
}

export function splitSteps(steps: ConversationStep[]): {
  reasoning: string;
  trace: ConversationStep[];
} {
  let reasoning = "";
  const trace: ConversationStep[] = [];

  for (const step of steps) {
    if (step.type === "reasoning") {
      reasoning += step.content;
    } else {
      trace.push(step);
    }
  }

  return { reasoning, trace };
}

export function coerceString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function looksJson(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}

export function parseResponse(value: string): unknown {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (!looksJson(trimmed)) return trimmed;

  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

function fenceJson(value: unknown): string {
  return `\\n\\n\\\u0060\\\u0060\\\u0060json\\n${JSON.stringify(value, null, 2)}\\n\\\u0060\\\u0060\\\u0060\\n`;
}

function formatScalar(value: unknown): string {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  if (value instanceof Date) return value.toISOString();
  return String(value);
}

function looksLikeCodeBlock(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  // Already-markdown code fences: keep as-is.
  if (trimmed.startsWith("```")) return true;
  // JSON-like content: render as json.
  if (looksJson(trimmed)) return true;

  // Heuristic: multiline + common code tokens/keywords.
  const isMultiline = value.includes("\n");
  if (!isMultiline) return false;

  const codeHints = [
    "{",
    "}",
    ";",
    "=>",
    "function ",
    "const ",
    "let ",
    "import ",
    "from ",
    "class ",
    "def ",
    "SELECT ",
    "CREATE ",
    "UPDATE ",
    "DELETE ",
  ];
  return codeHints.some((h) => value.includes(h));
}

function indentBlock(block: string, indent: number): string[] {
  const prefix = "  ".repeat(indent);
  return block.split("\n").map((line) => `${prefix}${line}`.trimEnd());
}

function markdownBullet(key: string, value: string, indent: number): string {
  const prefix = "  ".repeat(indent);
  return `${prefix}- **${key}**: ${value}`;
}

function formatMarkdownValue(value: unknown, depth: number): string {
  if (typeof value === "string") {
    if (!value.trim()) return "";
    const trimmed = value.trim();

    // If it looks like code/JSON, return a fenced block.
    if (looksLikeCodeBlock(value)) {
      if (looksJson(trimmed)) {
        try {
          return fenceJson(JSON.parse(trimmed));
        } catch {
          // Invalid JSON despite looking like it - render as plain code block
          return `\n\n\`\`\`\n${value}\n\`\`\`\n`;
        }
      }
      return `\n\n\`\`\`\n${value}\n\`\`\`\n`;
    }
    return value;
  }

  if (Array.isArray(value)) {
    if (depth >= 2 || value.length > 8) return fenceJson(value);
    if (value.length === 0) return "[]";

    const allScalars = value.every(
      (v) => v === null || ["string", "number", "boolean"].includes(typeof v),
    );
    if (allScalars) {
      return value.map((v) => formatScalar(v)).join(", ");
    }
    return fenceJson(value);
  }

  if (isPlainObject(value)) {
    const keys = Object.keys(value);
    if (depth >= 2 || keys.length > 10) return fenceJson(value);
    if (keys.length === 0) return "{}";
    return "__NESTED__";
  }

  return formatScalar(value);
}

function formatObjectAsMarkdownLines(
  obj: Record<string, unknown>,
  depth: number,
  indent: number,
): string[] {
  const lines: string[] = [];
  const keys = Object.keys(obj);
  for (const key of keys) {
    const value = obj[key];
    const formatted = formatMarkdownValue(value, depth);

    if (formatted === "__NESTED__" && isPlainObject(value)) {
      lines.push(`${"  ".repeat(indent)}- **${key}**:`);
      lines.push(...formatObjectAsMarkdownLines(value, depth + 1, indent + 1));
      continue;
    }

    if (typeof formatted === "string" && formatted.startsWith("\n\n```")) {
      lines.push(`${"  ".repeat(indent)}- **${key}**:`);
      lines.push(...indentBlock(formatted.trim(), indent + 1));
      continue;
    }

    // Multiline plain text: render as a block under the bullet (not code).
    if (typeof value === "string" && value.includes("\n") && value.trim()) {
      lines.push(`${"  ".repeat(indent)}- **${key}**:`);
      lines.push(...indentBlock(value.trimEnd(), indent + 1));
      continue;
    }

    lines.push(markdownBullet(key, formatted, indent));
  }

  return lines;
}

export function formatExtraDataMarkdown(data: Record<string, unknown>): string {
  const lines = formatObjectAsMarkdownLines(data, 0, 0);
  return lines.join("\n");
}
