import { ResponseStream } from "@/components/ui/response-stream";
import { Markdown } from "@/features/chat/components";
import { cn } from "@/lib/utils";
import type { Components } from "react-markdown";

export type StreamingMarkdownProps = {
  content: string;
  isStreaming: boolean;
  speed?: number;
  fadeDuration?: number;
  segmentDelay?: number;
  className?: string;
  components?: Partial<Components>;
};

export function StreamingMarkdown({
  content,
  isStreaming,
  speed = 50,
  fadeDuration = 200,
  segmentDelay = 30,
  className,
  components,
}: StreamingMarkdownProps) {
  if (isStreaming) {
    return (
      <div className={cn("prose prose-sm", className)}>
        <ResponseStream
          textStream={content}
          mode="fade"
          speed={speed}
          fadeDuration={fadeDuration}
          segmentDelay={segmentDelay}
        />
      </div>
    );
  }

  return (
    <Markdown
      className={cn("prose prose-sm", className)}
      components={components}
    >
      {content}
    </Markdown>
  );
}
