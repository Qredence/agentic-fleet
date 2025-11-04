import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";
import { StructuredMessageContent } from "./StructuredMessageContent";

interface ChatMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

/** Chat message component with structured content support */
export function ChatMessage({
  message,
  isStreaming = false,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div
      className={cn(
        "group w-full px-4 py-4",
        isUser && "bg-muted/30",
        isAssistant && "bg-background",
      )}
    >
      <div
        className={cn(
          "flex gap-3 max-w-4xl mx-auto",
          isUser ? "flex-row-reverse" : "flex-row",
        )}
      >
        {/* Avatar placeholder */}
        <div
          className={cn(
            "shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground",
          )}
        >
          {isUser ? "Y" : isAssistant ? "A" : "S"}
        </div>

        {/* Message content */}
        <div className={cn("flex-1 min-w-0", isUser && "text-right")}>
          {/* Header with role and timestamp */}
          <div
            className={cn(
              "flex items-center gap-2 mb-2 text-xs text-muted-foreground",
              isUser && "justify-end",
            )}
          >
            <span className="font-medium text-foreground">
              {isUser ? "You" : isAssistant ? "Assistant" : "System"}
            </span>
            {message.agentId && <span>({message.agentId})</span>}
            <span>{new Date(message.createdAt).toLocaleTimeString()}</span>
          </div>

          {/* Message bubble */}
          <div
            className={cn(
              "inline-block rounded-lg px-4 py-2 max-w-full",
              isUser
                ? "bg-primary text-primary-foreground ml-auto"
                : "bg-secondary text-secondary-foreground",
            )}
          >
            <StructuredMessageContent
              content={message.content}
              isStreaming={isStreaming}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Streaming message component */
interface StreamingMessageProps {
  content: string;
  agentId?: string;
}

export function StreamingMessage({ content, agentId }: StreamingMessageProps) {
  return (
    <div className="group w-full bg-background px-4 py-4">
      <div className="flex gap-3 max-w-4xl mx-auto">
        {/* Avatar placeholder */}
        <div className="shrink-0 w-8 h-8 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center text-sm font-medium">
          A
        </div>

        {/* Message content */}
        <div className="flex-1 min-w-0">
          {/* Header with role and timestamp */}
          <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Assistant</span>
            {agentId && <span>({agentId})</span>}
            <span>Streaming...</span>
          </div>

          {/* Message bubble */}
          <div className="inline-block rounded-lg px-4 py-2 max-w-full bg-secondary text-secondary-foreground">
            <StructuredMessageContent content={content} isStreaming={true} />
          </div>
        </div>
      </div>
    </div>
  );
}
