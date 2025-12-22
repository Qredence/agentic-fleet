import type { Message as ChatMessage } from "@/api/types";
import { cn } from "@/lib/utils";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollButton } from "./scroll-button";
import { ChatContainerContent, ChatContainerRoot } from "./chat-container";

import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/message";

/**
 * Formats message content for display, handling both string and non-string content.
 * Adds streaming cursor indicator when message is actively streaming.
 *
 * @param content - The message content (string or structured data)
 * @param isStreaming - Whether the message is currently being streamed
 * @returns Formatted string content with optional cursor indicator
 */
function formatMessageContent(content: unknown, isStreaming: boolean): string {
  const baseContent = typeof content === "string" ? content : JSON.stringify(content);
  return isStreaming ? baseContent + " ▍" : baseContent;
}

export type ChatMessagesProps = {
  messages: ChatMessage[];
  isLoading?: boolean;
  renderTrace?: (message: ChatMessage, isStreaming: boolean) => React.ReactNode;
  onCopy?: (content: string) => void;
  rootClassName?: string;
  contentClassName?: string;
};

export function ChatMessages({
  messages,
  isLoading = false,
  renderTrace,
  onCopy,
  rootClassName,
  contentClassName,
}: ChatMessagesProps) {
  return (
    <ChatContainerRoot className={cn("h-full", rootClassName)}>
      <ChatContainerContent className={cn("px-4 py-8", contentClassName)}>
        <div className="flex flex-col gap-6">
          {messages.map((message, index) => {
            const isAssistant = message.role === "assistant";
            const isLastMessage = index === messages.length - 1;
            const isStreaming = isAssistant && isLastMessage && isLoading;
            // Use message ID if available, fallback to content-based key for stability
            // Avoid pure index keys which cause reconciliation issues
            const messageKey =
              message.id ||
              `${message.role}-${message.created_at || index}-${String(message.content).slice(0, 20)}`;

            if (!isAssistant) {
              return (
                <Message
                  key={messageKey}
                  className="mx-auto w-full max-w-3xl justify-end px-4"
                >
                  <MessageContent className="bg-secondary/80 text-foreground border-border/50 max-w-[85%] rounded-2xl border px-4 py-2.5 backdrop-blur-sm sm:max-w-[75%] whitespace-pre-wrap break-normal">
                    {message.content}
                  </MessageContent>
                </Message>
              );
            }

            return (
              <Message
                key={messageKey}
                className="mx-auto w-full max-w-3xl flex-col gap-2 px-4 items-start"
              >
                {renderTrace ? renderTrace(message, isStreaming) : null}

                <div className="group flex w-full flex-col gap-0">
                  <MessageContent
                    className={cn(
                      "text-foreground prose flex-1 rounded-lg bg-transparent p-0",
                      isStreaming && "whitespace-pre-wrap",
                    )}
                    markdown={true}
                  >
                    {formatMessageContent(message.content, isStreaming)}
                  </MessageContent>

                  {!isStreaming && (
                    <MessageActions className="-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                          onClick={() => {
                            if (onCopy) {
                              onCopy(message.content);
                            } else {
                              void navigator.clipboard.writeText(
                                message.content,
                              );
                            }
                          }}
                          aria-label="Copy response"
                        >
                          <Copy className="size-4" />
                        </Button>
                      </MessageAction>
                    </MessageActions>
                  )}
                </div>
              </Message>
            );
          })}
        </div>
      </ChatContainerContent>

      <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-4">
        <ScrollButton className="shadow-sm" />
      </div>
    </ChatContainerRoot>
  );
}
