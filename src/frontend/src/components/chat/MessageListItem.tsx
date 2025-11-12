import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";
import {
  Message,
  MessageAvatar,
  MessageActions,
  MessageAction,
} from "@/components/ui/message";
import { Button } from "@/components/ui/button";
import { StructuredMessageContent } from "@/components/chat/StructuredMessageContent";
import { ReasoningDisplay } from "@/components/chat/ReasoningDisplay";
import { Copy, ThumbsUp, ThumbsDown } from "lucide-react";
import { memo } from "react";

interface MessageListItemProps {
  message: ChatMessage;
  isStreamingMessage: boolean;
  isLastMessage: boolean;
  currentReasoningContent?: string;
  currentReasoningStreaming?: boolean;
}

export const MessageListItem = memo(function MessageListItem({
  message,
  isStreamingMessage,
  isLastMessage,
  currentReasoningContent,
  currentReasoningStreaming,
}: MessageListItemProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const timestamp = new Date(message.createdAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const avatarFallback = isUser
    ? "Y"
    : (message.agentId?.slice(0, 2).toUpperCase() ?? "AI");

  const isFinalAssistantMessage =
    isAssistant && !isStreamingMessage && isLastMessage;

  return (
    <Message
      key={message.id}
      className={cn(
        "group w-full max-w-[700px] items-start gap-3 md:gap-4",
        isUser ? "ml-auto flex-row-reverse" : "mr-auto",
      )}
    >
      <MessageAvatar
        src=""
        alt={isUser ? "User avatar" : "Assistant avatar"}
        fallback={avatarFallback}
        className={cn(
          "border border-border",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-secondary-foreground",
        )}
      />

      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col gap-2",
          isUser ? "items-end text-right" : "items-start text-left",
        )}
      >
        <div
          className={cn(
            "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
            isUser ? "justify-end" : "justify-start",
          )}
        >
          <span className="font-medium text-foreground">
            {isUser ? "You" : "Assistant"}
          </span>
          {isAssistant && message.agentId && (
            <span className="text-muted-foreground">· {message.agentId}</span>
          )}
          <span>{timestamp}</span>
        </div>

        <div
          className={cn(
            "flex w-full flex-col gap-3",
            isUser ? "items-end" : "items-start",
          )}
        >
          {isAssistant &&
            (message.reasoning ||
              (isStreamingMessage && currentReasoningContent)) && (
              <div className="w-full">
                <ReasoningDisplay
                  content={
                    isStreamingMessage && currentReasoningContent
                      ? currentReasoningContent
                      : message.reasoning
                  }
                  isStreaming={
                    isStreamingMessage && !!currentReasoningStreaming
                  }
                  triggerText="Model reasoning"
                  defaultOpen={
                    isStreamingMessage && !!currentReasoningStreaming
                  }
                />
              </div>
            )}

          <div
            className={cn(
              "max-w-[90%] rounded-3xl px-5 py-3 text-sm leading-relaxed shadow-none sm:max-w-[75%]",
              isUser
                ? "bg-[#F4F4F5] text-foreground border border-transparent"
                : "bg-transparent text-foreground border border-transparent",
            )}
          >
            <StructuredMessageContent
              content={message.content}
              isStreaming={isStreamingMessage}
              forcePlain={isFinalAssistantMessage}
              className={cn(
                "max-w-none leading-relaxed",
                isUser
                  ? "[--tw-prose-body:var(--color-primary-foreground)] [--tw-prose-headings:var(--color-primary-foreground)] prose-strong:text-primary-foreground"
                  : "[--tw-prose-body:var(--color-foreground)] [--tw-prose-headings:var(--color-foreground)]",
              )}
            />
          </div>
        </div>

        {isStreamingMessage && (
          <span
            className="flex items-center gap-2 text-xs text-muted-foreground"
            role="status"
            aria-live="polite"
          >
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary" />
            {message.agentId
              ? `Streaming from ${message.agentId}`
              : "Streaming…"}
          </span>
        )}

        <MessageActions
          className={cn(
            "flex gap-1 text-xs text-muted-foreground transition-opacity duration-150",
            isUser ? "justify-end" : "justify-start",
            isLastMessage || isUser
              ? "opacity-100"
              : "opacity-0 group-hover:opacity-100",
          )}
        >
          <MessageAction tooltip="Copy" delayDuration={100}>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full"
              aria-label="Copy message"
            >
              <Copy size={16} />
            </Button>
          </MessageAction>
          {isAssistant && (
            <>
              <MessageAction tooltip="Upvote" delayDuration={100}>
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  aria-label="Upvote message"
                >
                  <ThumbsUp size={16} />
                </Button>
              </MessageAction>
              <MessageAction tooltip="Downvote" delayDuration={100}>
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  aria-label="Downvote message"
                >
                  <ThumbsDown size={16} />
                </Button>
              </MessageAction>
            </>
          )}
        </MessageActions>
      </div>
    </Message>
  );
}, areEqual);

function areEqual(prev: MessageListItemProps, next: MessageListItemProps) {
  // For streaming messages, always re-render to show real-time updates
  if (prev.isStreamingMessage || next.isStreamingMessage) {
    return false;
  }

  return (
    prev.isStreamingMessage === next.isStreamingMessage &&
    prev.isLastMessage === next.isLastMessage &&
    prev.currentReasoningContent === next.currentReasoningContent &&
    prev.currentReasoningStreaming === next.currentReasoningStreaming &&
    prev.message.id === next.message.id &&
    prev.message.content === next.message.content &&
    prev.message.agentId === next.message.agentId &&
    prev.message.role === next.message.role &&
    prev.message.reasoning === next.message.reasoning &&
    prev.message.reasoningStreaming === next.message.reasoningStreaming &&
    prev.message.createdAt === next.message.createdAt
  );
}
