import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { Markdown } from "./markdown";
import { StreamingMarkdown } from "./streaming-markdown";
import type { MarkdownProps } from "./markdown";

export type MessageProps = {
  children: React.ReactNode;
  className?: string;
} & React.HTMLProps<HTMLDivElement>;

const Message = ({ children, className, ...props }: MessageProps) => (
  <div className={cn("flex gap-3", className)} {...props}>
    {children}
  </div>
);

export type MessageAvatarProps = {
  src: string;
  alt: string;
  fallback?: string;
  delayMs?: number;
  className?: string;
};

const MessageAvatar = ({
  src,
  alt,
  fallback,
  delayMs,
  className,
}: MessageAvatarProps) => {
  return (
    <Avatar className={cn("h-8 w-8 shrink-0", className)}>
      <AvatarImage src={src} alt={alt} />
      {fallback && (
        <AvatarFallback delayMs={delayMs}>{fallback}</AvatarFallback>
      )}
    </Avatar>
  );
};

export type MessageContentProps = {
  children: React.ReactNode;
  markdown?: boolean;
  className?: string;
  id?: string;
  components?: MarkdownProps["components"];
  isStreaming?: boolean;
  streamSpeed?: number;
  fadeDuration?: number;
  segmentDelay?: number;
} & React.HTMLProps<HTMLDivElement>;

/**
 * Converts JSON artifact content to readable format.
 * Handles patterns like "Updated artifact (JSON): { ... }"
 * and converts to formatted text like "Result summary: ..."
 */
function formatJsonArtifact(content: string): string {
  // Pattern to match "Updated artifact (JSON):" followed by JSON
  const jsonPattern = /Updated artifact\s*\(JSON\):\s*(\{[\s\S]*\})(?=\s|$)/g;

  return content.replace(jsonPattern, (match, jsonStr) => {
    try {
      // Try to find complete JSON object (may span multiple lines)
      // Look for balanced braces
      let braceCount = 0;
      let jsonStart = -1;
      let jsonEnd = -1;

      for (let i = 0; i < jsonStr.length; i++) {
        if (jsonStr[i] === "{") {
          if (braceCount === 0) jsonStart = i;
          braceCount++;
        } else if (jsonStr[i] === "}") {
          braceCount--;
          if (braceCount === 0) {
            jsonEnd = i + 1;
            break;
          }
        }
      }

      if (jsonStart >= 0 && jsonEnd > jsonStart) {
        const extractedJson = jsonStr.slice(jsonStart, jsonEnd);
        try {
          const parsed = JSON.parse(extractedJson);

          // Format as readable text with labels
          const parts: string[] = [];

          // Common field mappings to readable labels
          const fieldLabels: Record<string, string> = {
            result_summary: "Result summary",
            explainer_text: "Explainer text",
            figure_caption: "Figure caption",
            observation_activity: "Observation activity",
          };

          for (const [key, value] of Object.entries(parsed)) {
            const label =
              fieldLabels[key] ||
              key
                .split("_")
                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                .join(" ");

            if (typeof value === "string" && value.trim()) {
              parts.push(`**${label}:**\n\n${value.trim()}`);
            } else if (value !== null && value !== undefined) {
              parts.push(`**${label}:**\n\n${String(value)}`);
            }
          }

          return parts.join("\n\n---\n\n");
        } catch {
          // Not valid JSON, return original
          return match;
        }
      }
    } catch {
      // Parsing failed, return original
    }
    return match;
  });
}

const MessageContent = ({
  children,
  markdown = false,
  className,
  id,
  components,
  isStreaming = false,
  streamSpeed = 50,
  fadeDuration = 200,
  segmentDelay = 30,
  ...props
}: MessageContentProps) => {
  // For markdown mode, let Streamdown handle whitespace; for plain text, use pre-wrap
  const classNames = cn(
    "rounded-lg p-2 text-foreground bg-secondary prose break-words",
    !markdown && "whitespace-pre-wrap", // Only add whitespace-pre-wrap for non-markdown content
    className,
  );

  if (markdown && typeof children !== "string") {
    console.warn("MessageContent: markdown mode requires string children");
  }

  // Pre-process content to format JSON artifacts as readable text
  const processedContent =
    markdown && typeof children === "string"
      ? formatJsonArtifact(children)
      : typeof children === "string"
        ? children
        : String(children ?? "");

  // Streaming with markdown: use StreamingMarkdown
  if (markdown && isStreaming && typeof children === "string") {
    return (
      <StreamingMarkdown
        content={processedContent}
        isStreaming={isStreaming}
        speed={streamSpeed}
        fadeDuration={fadeDuration}
        segmentDelay={segmentDelay}
        className={classNames}
        components={components}
      />
    );
  }

  // Static rendering: existing behavior
  return markdown ? (
    <Markdown className={classNames} id={id} components={components}>
      {processedContent}
    </Markdown>
  ) : (
    <div className={classNames} {...props}>
      {children}
    </div>
  );
};

export type MessageActionsProps = {
  children: React.ReactNode;
  className?: string;
} & React.HTMLProps<HTMLDivElement>;

const MessageActions = ({
  children,
  className,
  ...props
}: MessageActionsProps) => (
  <div
    className={cn("text-muted-foreground flex items-center gap-2", className)}
    {...props}
  >
    {children}
  </div>
);

export type MessageActionProps = {
  className?: string;
  tooltip: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
} & React.ComponentProps<typeof Tooltip>;

const MessageAction = ({
  tooltip,
  children,
  className,
  side = "top",
  ...props
}: MessageActionProps) => {
  return (
    <Tooltip {...props}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side} className={className}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
};

export {
  Message,
  MessageAvatar,
  MessageContent,
  MessageActions,
  MessageAction,
};
