import type {
  MessagePattern,
  ParsedMessage,
  ReasoningSection,
  StepItem,
  ThoughtNode,
} from "@/types/chat";

interface ParseMessageOptions {
  kind?: string;
}

const TASK_LEDGER_FACTS_HEADER = /Here is an initial fact sheet to consider:/i;
const TASK_LEDGER_PLAN_HEADER =
  /Here is the plan to follow as best as possible:/i;
const MAX_PLAN_STEPS = 10;
const MAX_THOUGHT_NODES = 30;

/**
 * Lightweight title case helper for section titles.
 */
function toTitleCase(value: string): string {
  return value
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase())
    .trim();
}

/**
 * Best-effort JSON extractor for ledger content.
 */
function parseJson(content: string): unknown {
  const trimmed = content.trim();
  const fencedMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fencedMatch ? fencedMatch[1].trim() : trimmed;

  const attempts = [
    candidate,
    candidate
      .replace(/\bTrue\b/g, "true")
      .replace(/\bFalse\b/g, "false")
      .replace(/\bNone\b/g, "null"),
  ];

  for (const attempt of attempts) {
    try {
      return JSON.parse(attempt);
    } catch {
      continue;
    }
  }

  // Last chance: try to slice out the first balanced JSON object.
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) {
    const slice = candidate.slice(start, end + 1);
    try {
      return JSON.parse(slice);
    } catch {
      return null;
    }
  }

  return null;
}

/**
 * Convert task ledger facts section into ReasoningSection objects.
 */
function parseTaskLedgerFactsSection(content: string): ReasoningSection[] {
  const sections: ReasoningSection[] = [];
  const lines = content.split("\n");
  let current: ReasoningSection | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    const headerMatch = line.match(/^(\d+)\.\s*(.+)$/);
    if (headerMatch) {
      if (current) {
        current.content = current.content.trim();
        if (current.content) {
          sections.push(current);
        }
      }
      current = {
        title: toTitleCase(headerMatch[2]),
        content: "",
        type: "reason",
      };
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s*(.+)$/);
    if (bulletMatch) {
      if (current) {
        current.content = current.content.trim();
        if (current.content) {
          sections.push(current);
        }
      }
      current = {
        title: toTitleCase(bulletMatch[1]),
        content: "",
        type: "reason",
      };
      continue;
    }

    if (!current) {
      current = {
        title: "Facts",
        content: line,
        type: "reason",
      };
      continue;
    }

    current.content = current.content ? `${current.content}\n${line}` : line;
  }

  if (current) {
    current.content = current.content.trim();
    if (current.content) {
      sections.push(current);
    }
  }

  return sections;
}

/**
 * Parse Magentic progress ledger JSON into ReasoningSection items.
 */
function parseProgressLedger(content: string): ParsedMessage {
  const parsed = parseJson(content);

  if (!parsed || typeof parsed !== "object" || parsed === null) {
    return {
      pattern: "plain",
      data: { plain: content },
    };
  }

  const sections: ReasoningSection[] = [];

  for (const [rawKey, rawValue] of Object.entries(parsed)) {
    let sectionContent = "";

    if (rawValue && typeof rawValue === "object" && "reason" in rawValue) {
      const valueObj = rawValue as Record<string, unknown>;
      const reason =
        typeof valueObj.reason === "string" ? valueObj.reason.trim() : "";
      const answer = valueObj.answer;

      const parts: string[] = [];
      if (reason) {
        parts.push(reason);
      }
      if (answer !== undefined) {
        if (typeof answer === "boolean") {
          parts.push(`Answer: ${answer ? "Yes" : "No"}`);
        } else if (answer !== null) {
          parts.push(`Answer: ${String(answer)}`);
        }
      }

      sectionContent = parts.join("\n\n");
    } else {
      sectionContent = JSON.stringify(rawValue, null, 2);
    }

    if (!sectionContent) continue;

    sections.push({
      title: toTitleCase(rawKey),
      content: sectionContent,
      type: "reason",
    });
  }

  if (!sections.length) {
    return {
      pattern: "plain",
      data: { plain: content },
    };
  }

  return {
    pattern: "reasoning",
    data: { reasoning: sections },
  };
}

/**
 * Parse Magentic task ledger content.
 */
function parseTaskLedger(content: string): ParsedMessage {
  const planSplit = content.split(TASK_LEDGER_PLAN_HEADER);
  const planSection = planSplit[1]?.trim() ?? "";

  const factsSplit = planSplit[0]?.split(TASK_LEDGER_FACTS_HEADER) ?? [];
  const introSection = factsSplit[0]?.trim() ?? "";
  const factsSection = factsSplit[1]?.trim() ?? "";

  const steps = planSection ? parseSteps(planSection) : [];
  const reasoning = factsSection
    ? parseTaskLedgerFactsSection(factsSection)
    : [];

  const data: ParsedMessage["data"] = {};

  if (steps.length) {
    const limitedSteps = steps.slice(0, MAX_PLAN_STEPS).map((step, idx) => ({
      ...step,
      index: idx + 1,
    }));
    data.steps = limitedSteps;

    if (steps.length > MAX_PLAN_STEPS) {
      const overflow = steps
        .slice(MAX_PLAN_STEPS)
        .map((step) => `- ${step.content}`)
        .join("\n");
      data.plain = data.plain
        ? `${data.plain}\n\nAdditional plan details:\n${overflow}`
        : `Additional plan details:\n${overflow}`;
    }
  }
  if (reasoning.length) {
    data.reasoning = reasoning.slice(0, MAX_PLAN_STEPS);
  }
  if (introSection) {
    data.plain = data.plain ? `${introSection}\n\n${data.plain}` : introSection;
  }

  const hasSteps = Boolean(data.steps?.length);
  const hasReasoning = Boolean(data.reasoning?.length);

  let pattern: MessagePattern = "plain";
  if (hasSteps && hasReasoning) {
    pattern = "mixed";
  } else if (hasSteps) {
    pattern = "steps";
  } else if (hasReasoning) {
    pattern = "reasoning";
  } else {
    data.plain = content;
  }

  return { pattern, data };
}

/**
 * Detects the dominant pattern in a message
 */
export function detectPattern(content: string): MessagePattern {
  const hasSteps = detectStepsPattern(content);
  const hasReasoning = detectReasoningPattern(content);
  const hasChainOfThought = detectChainOfThoughtPattern(content);

  const patternCount = [hasSteps, hasReasoning, hasChainOfThought].filter(
    Boolean,
  ).length;

  if (patternCount > 1) {
    return "mixed";
  }
  if (hasSteps) {
    return "steps";
  }
  if (hasReasoning) {
    return "reasoning";
  }
  if (hasChainOfThought) {
    return "chain_of_thought";
  }
  return "plain";
}

/**
 * Detects if content contains steps pattern
 */
function detectStepsPattern(content: string): boolean {
  const stepPatterns = [
    /^\d+\.\s/m, // Numbered list: "1. "
    /^[-•*]\s/m, // Bullet points: "- ", "• ", "* "
    /^[A-Z]\.\s/m, // Lettered list: "A. "
    /^(plan|steps|tasks|actions):/im, // Headers: "Plan:", "Steps:"
  ];
  return stepPatterns.some((pattern) => pattern.test(content));
}

/**
 * Detects if content contains reasoning pattern
 */
function detectReasoningPattern(content: string): boolean {
  const reasoningPatterns = [
    /^(reason|explanation|because|rationale|why):/im,
    /\b(therefore|thus|hence|consequently)\b/i,
  ];
  return reasoningPatterns.some((pattern) => pattern.test(content));
}

/**
 * Detects if content contains chain of thought pattern
 */
function detectChainOfThoughtPattern(content: string): boolean {
  const cotPatterns = [
    /^(first|then|next|finally|given|therefore)[:,\s]/im,
    /fact\s*\d+:/i,
    /step\s*\d+:/i,
  ];
  return cotPatterns.some((pattern) => pattern.test(content));
}

/**
 * Parses content into steps
 */
export function parseSteps(content: string): StepItem[] {
  const steps: StepItem[] = [];
  const lines = content.split("\n");
  let currentIndex = 0;

  for (const line of lines) {
    const trimmedLine = line.trim();
    if (!trimmedLine) continue;

    // Match numbered lists: "1. Step content"
    const numberedMatch = trimmedLine.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      steps.push({
        index: parseInt(numberedMatch[1], 10) - 1,
        content: numberedMatch[2],
        completed: false,
        label: numberedMatch[1],
      });
      currentIndex = steps.length;
      continue;
    }

    // Match lettered lists: "A. Step content"
    const letterMatch = trimmedLine.match(/^([A-Z])\.\s+(.+)$/);
    if (letterMatch) {
      steps.push({
        index: currentIndex,
        content: letterMatch[2],
        completed: false,
        label: letterMatch[1],
      });
      currentIndex++;
      continue;
    }

    // Match bullet points: "- Step content" or "• Step content"
    const bulletMatch = trimmedLine.match(/^[-•*]\s+(.+)$/);
    if (bulletMatch) {
      steps.push({
        index: currentIndex,
        content: bulletMatch[1],
        completed: false,
      });
      currentIndex++;
      continue;
    }

    // Match indented substeps
    if (line.match(/^\s{2,}/) && steps.length > 0) {
      const lastStep = steps[steps.length - 1];
      if (!lastStep.substeps) {
        lastStep.substeps = [];
      }
      lastStep.substeps.push({
        index: lastStep.substeps.length,
        content: trimmedLine.replace(/^[-•*]\s+/, ""),
        completed: false,
      });
    }
  }

  return steps;
}

/**
 * Parses content into reasoning sections
 */
export function parseReasoning(content: string): ReasoningSection[] {
  const sections: ReasoningSection[] = [];
  const lines = content.split("\n");
  let currentSection: ReasoningSection | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Match reasoning headers
    const headerMatch = line.match(
      /^(reason|explanation|rationale|because|why):\s*(.*)$/i,
    );
    if (headerMatch) {
      // Save previous section
      if (currentSection) {
        sections.push(currentSection);
      }

      const title = headerMatch[1];
      const initialContent = headerMatch[2];

      currentSection = {
        title,
        content: initialContent,
        type: title.toLowerCase().includes("reason")
          ? "reason"
          : title.toLowerCase().includes("explanation")
            ? "explanation"
            : "rationale",
      };
      continue;
    }

    // Add to current section if exists
    if (currentSection && line) {
      currentSection.content += "\n" + line;
    }
  }

  // Add last section
  if (currentSection) {
    sections.push(currentSection);
  }

  return sections;
}

/**
 * Parses content into chain of thought nodes
 */
export function parseChainOfThought(content: string): ThoughtNode[] {
  const thoughts: ThoughtNode[] = [];
  const lines = content.split("\n");
  let nodeCounter = 0;

  for (const line of lines) {
    const trimmedLine = line.trim();
    if (!trimmedLine) continue;

    // Detect thought type based on keywords
    let type: ThoughtNode["type"] = "fact";
    if (
      /^(first|given|fact|observe)/i.test(trimmedLine) ||
      trimmedLine.includes(":")
    ) {
      type = "fact";
    } else if (/^(then|next|therefore|thus)/i.test(trimmedLine)) {
      type = "deduction";
    } else if (/^(finally|conclude|decide)/i.test(trimmedLine)) {
      type = "decision";
    }

    if (
      thoughts.length === 0 ||
      thoughts[thoughts.length - 1].content !== trimmedLine
    ) {
      thoughts.push({
        id: `thought-${nodeCounter++}`,
        content: trimmedLine,
        timestamp: Date.now() + nodeCounter,
        type,
      });
    }
    if (thoughts.length >= MAX_THOUGHT_NODES) {
      break;
    }
  }

  return thoughts;
}

/**
 * Main parser function that analyzes content and returns structured data
 */
export function parseMessage(
  content: string,
  options: ParseMessageOptions = {},
): ParsedMessage {
  const kind = options.kind?.toLowerCase();

  if (kind === "progress_ledger") {
    return parseProgressLedger(content);
  }

  if (kind === "task_ledger") {
    return parseTaskLedger(content);
  }

  if (kind === "facts") {
    const reasoning = parseTaskLedgerFactsSection(content);
    if (reasoning.length) {
      return {
        pattern: "reasoning",
        data: { reasoning },
      };
    }
  }

  const pattern = detectPattern(content);

  const data: ParsedMessage["data"] = {};

  const shouldApplyHeuristics =
    kind !== undefined ||
    pattern !== "plain" ||
    /^(plan|steps|task|reason)/im.test(content);

  if (!shouldApplyHeuristics) {
    return {
      pattern: "plain",
      data: { plain: content },
    };
  }

  switch (pattern) {
    case "steps": {
      const parsedSteps = parseSteps(content);
      if (parsedSteps.length >= 2) {
        data.steps = parsedSteps;
        break;
      }
      data.plain = content;
      break;
    }
    case "reasoning": {
      const parsedReasoning = parseReasoning(content);
      if (parsedReasoning.length) {
        data.reasoning = parsedReasoning;
        break;
      }
      data.plain = content;
      break;
    }
    case "chain_of_thought": {
      const thoughts = parseChainOfThought(content);
      if (thoughts.length) {
        data.thoughts = thoughts;
        break;
      }
      data.plain = content;
      break;
    }
    case "mixed":
      data.steps = parseSteps(content);
      data.reasoning = parseReasoning(content);
      data.thoughts = parseChainOfThought(content);
      if (
        !data.steps?.length &&
        !data.reasoning?.length &&
        !data.thoughts?.length
      ) {
        data.plain = content;
      }
      break;
    case "plain":
    default:
      data.plain = content;
      break;
  }

  if (
    !data.steps?.length &&
    !data.reasoning?.length &&
    !data.thoughts?.length
  ) {
    data.plain = content;
    return { pattern: "plain", data };
  }

  return { pattern, data };
}
