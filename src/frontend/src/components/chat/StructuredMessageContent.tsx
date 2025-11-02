import { parseMessage } from "@/lib/parsers/messageParser";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { ChainOfThoughtDisplay } from "./ChainOfThoughtDisplay";
import { ReasoningDisplay } from "./ReasoningDisplay";
import { StepsDisplay } from "./StepsDisplay";

interface StructuredMessageContentProps {
  content: string;
  isStreaming?: boolean;
}

/**
 * StructuredMessageContent intelligently parses and renders message content
 * using appropriate display components (Steps, Reasoning, Chain of Thought)
 */
export function StructuredMessageContent({
  content,
  isStreaming = false,
}: StructuredMessageContentProps) {
  const parsedMessage = useMemo(() => parseMessage(content), [content]);

  // For plain messages or when pattern detection fails, use standard markdown
  if (parsedMessage.pattern === "plain" || !parsedMessage.data) {
    return (
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const language = match ? match[1] : "";
              return !inline && match ? (
                <div className="relative">
                  <SyntaxHighlighter
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
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  // Render structured content based on detected pattern
  return (
    <div className="space-y-4">
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
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {parsedMessage.data.plain}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
