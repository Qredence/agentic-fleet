import type {
  MessagePattern,
  ParsedMessage,
  StepItem,
  ReasoningSection,
  ThoughtNode,
} from "@/types/chat";

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
        index: parseInt(numberedMatch[1], 10),
        content: numberedMatch[2],
        completed: false,
      });
      currentIndex++;
      continue;
    }

    // Match bullet points: "- Step content" or "• Step content"
    const bulletMatch = trimmedLine.match(/^[-•*]\s+(.+)$/);
    if (bulletMatch) {
      steps.push({
        index: currentIndex++,
        content: bulletMatch[1],
        completed: false,
      });
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

    thoughts.push({
      id: `thought-${nodeCounter++}`,
      content: trimmedLine,
      timestamp: Date.now() + nodeCounter,
      type,
    });
  }

  return thoughts;
}

/**
 * Main parser function that analyzes content and returns structured data
 */
export function parseMessage(content: string): ParsedMessage {
  const pattern = detectPattern(content);

  const data: ParsedMessage["data"] = {};

  switch (pattern) {
    case "steps":
      data.steps = parseSteps(content);
      break;
    case "reasoning":
      data.reasoning = parseReasoning(content);
      break;
    case "chain_of_thought":
      data.thoughts = parseChainOfThought(content);
      break;
    case "mixed":
      // Try to parse all patterns
      data.steps = parseSteps(content);
      data.reasoning = parseReasoning(content);
      data.thoughts = parseChainOfThought(content);
      break;
    case "plain":
    default:
      data.plain = content;
      break;
  }

  return { pattern, data };
}
