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
        "group flex w-full gap-4 px-4 py-4",
        isUser && "bg-muted/30",
        isAssistant && "bg-background",
      )}
    >
      <div className="flex w-full max-w-4xl flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {isUser ? "You" : isAssistant ? "Assistant" : "System"}
          </span>
          {message.agentId && (
            <span className="text-xs text-muted-foreground">
              ({message.agentId})
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            {new Date(message.createdAt).toLocaleTimeString()}
          </span>
        </div>
        <StructuredMessageContent
          content={message.content}
          isStreaming={isStreaming}
        />
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
    <div className="group flex w-full gap-4 bg-background px-4 py-4">
      <div className="flex w-full max-w-4xl flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Assistant</span>
          {agentId && (
            <span className="text-xs text-muted-foreground">({agentId})</span>
          )}
          <span className="text-xs text-muted-foreground">Streaming...</span>
        </div>
        <StructuredMessageContent content={content} isStreaming={true} />
      </div>
    </div>
  );
}
