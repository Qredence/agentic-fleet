import { parseMessage, parseSteps } from "@/lib/parsers/messageParser";
import { cn } from "@/lib/utils";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { ChainOfThoughtDisplay } from "./ChainOfThoughtDisplay";
import { ReasoningDisplay } from "./ReasoningDisplay";
import { StepsDisplay } from "./StepsDisplay";
import type { StepItem } from "@/types/chat";

interface StructuredMessageContentProps {
  content: string;
  isStreaming?: boolean;
  kind?: string;
  className?: string;
  forcePlain?: boolean;
}

/**
 * StructuredMessageContent intelligently parses and renders message content
 * using appropriate display components (Steps, Reasoning, Chain of Thought)
 */
export function StructuredMessageContent({
  content,
  isStreaming = false,
  kind,
  className,
  forcePlain = false,
}: StructuredMessageContentProps) {
  const inlinePlan = useMemo(
    () => (!kind && !forcePlain ? extractInlinePlan(content) : null),
    [content, kind, forcePlain],
  );
  const baseContent =
    forcePlain || !inlinePlan || isStreaming || kind
      ? content
      : inlinePlan.rest;

  const parsedMessage = useMemo(() => {
    if (isStreaming || forcePlain) {
      return {
        pattern: "plain" as const,
        data: { plain: baseContent },
      };
    }
    return parseMessage(baseContent, { kind });
  }, [baseContent, kind, isStreaming, forcePlain]);

  if (isStreaming || forcePlain) {
    return (
      <div
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none prose-headings:m-0 prose-p:m-0",
          className,
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{baseContent}</ReactMarkdown>
      </div>
    );
  }

  // For plain messages or when pattern detection fails, use standard markdown
  if (parsedMessage.pattern === "plain" || !parsedMessage.data) {
    return (
      <div
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none prose-headings:m-0 prose-p:m-0",
          className,
        )}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const language = match ? match[1] : "";
              const isInline = !className?.includes("language-");
              return !isInline && match ? (
                <div className="relative -mx-4">
                  <SyntaxHighlighter
                    // @ts-expect-error - vscDarkPlus type doesn't match the expected type signature
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    className="rounded-lg"
                    {...props}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {baseContent}
        </ReactMarkdown>
      </div>
    );
  }

  // Render structured content based on detected pattern
  return (
    <div className={cn("space-y-4", className)}>
      {inlinePlan?.steps?.length ? (
        <StepsDisplay
          steps={inlinePlan.steps}
          title={inlinePlan.title}
          isStreaming={isStreaming}
          defaultOpen
        />
      ) : null}

      {inlinePlan?.lead && (
        <div className="text-sm text-muted-foreground">{inlinePlan.lead}</div>
      )}

      {/* Render Steps if present */}
      {parsedMessage.data.steps && parsedMessage.data.steps.length > 0 && (
        <StepsDisplay
          steps={parsedMessage.data.steps}
          isStreaming={isStreaming}
          defaultOpen={parsedMessage.pattern === "steps"}
        />
      )}

      {/* Render Reasoning if present */}
      {parsedMessage.data.reasoning &&
        parsedMessage.data.reasoning.length > 0 && (
          <ReasoningDisplay
            sections={parsedMessage.data.reasoning}
            isStreaming={isStreaming}
            defaultOpen={parsedMessage.pattern === "reasoning"}
          />
        )}

      {/* Render Chain of Thought if present */}
      {parsedMessage.data.thoughts &&
        parsedMessage.data.thoughts.length > 0 && (
          <ChainOfThoughtDisplay
            thoughts={parsedMessage.data.thoughts}
            isStreaming={isStreaming}
            defaultOpen={parsedMessage.pattern === "chain_of_thought"}
          />
        )}

      {/* Render any remaining plain text for mixed content */}
      {parsedMessage.pattern === "mixed" && parsedMessage.data.plain && (
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:m-0 prose-p:m-0">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {parsedMessage.data.plain}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

interface InlinePlanResult {
  steps: StepItem[];
  title: string;
  rest: string;
  lead?: string;
}

function extractInlinePlan(
  content: string,
  kind?: string,
): InlinePlanResult | null {
  if (kind) {
    return null;
  }

  const lines = content.split("\n");
  const planIndex = lines.findIndex((line) => /^\s*plan\b/i.test(line));
  if (planIndex === -1) {
    return null;
  }

  const stepsLines: string[] = [];
  let i = planIndex + 1;
  for (; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*\d+\.\s+/.test(line)) {
      stepsLines.push(line.trim());
      continue;
    }
    if (!line.trim() && stepsLines.length) {
      continue;
    }
    if (stepsLines.length === 0) {
      continue;
    }
    break;
  }

  if (!stepsLines.length) {
    return null;
  }

  const uniqueSteps = stepsLines.filter((line, idx, arr) => {
    const normalized = line.toLowerCase();
    return arr.findIndex((other) => other.toLowerCase() === normalized) === idx;
  });

  const parsedSteps = parseSteps(uniqueSteps.join("\n")).map((step, idx) => ({
    ...step,
    index: idx,
  }));

  const restLines = [...lines];
  const removalCount = i - planIndex;
  restLines.splice(planIndex, removalCount);
  const rest = restLines
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  const headingLine = lines[planIndex].trim();
  const title = "Plan";
  const lead = headingLine.replace(/^plan\b[:\s-]*/i, "").trim() || undefined;

  return {
    steps: parsedSteps,
    title,
    rest,
    lead,
  };
}
