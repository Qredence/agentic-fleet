import { useRef, useState } from "react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import type { Message as ChatMessage } from "@/api/types";
import { cn } from "@/lib/utils";
import { Copy, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollButton } from "./scroll-button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { TracePanel } from "./TracePanel";

import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/features/chat/components";

export type ChatMessagesProps = {
  messages: ChatMessage[];
  isLoading?: boolean;
  renderTrace?: (message: ChatMessage, isStreaming: boolean) => React.ReactNode;
  onCopy?: (content: string) => void;
  rootClassName?: string;
  contentClassName?: string;
  streamSpeed?: number;
  fadeDuration?: number;
  segmentDelay?: number;
};

/**
 * Render the chat message list with distinct layouts for assistant and user messages, optional trace rendering, per-message copy actions, and a bottom-centered scroll button.
 *
 * - Assistant messages are left-aligned, support markdown rendering, and show a streaming cursor when the last assistant message is streaming.
 * - User messages are right-aligned and shown in a compact bubble.
 *
 * @param messages - Array of chat messages to render.
 * @param isLoading - When true, the last assistant message is treated as streaming and displays a streaming cursor.
 * @param renderTrace - Optional function to render trace UI for an assistant message: called with (message, isStreaming).
 * @param onCopy - Optional handler called with a message's content when the copy action is invoked; if omitted, the browser clipboard is used.
 * @param rootClassName - Optional additional class name applied to the root chat container.
 * @param contentClassName - Optional additional class name applied to the content container.
 * @returns A React element containing the rendered messages and scroll control.
 */
export function ChatMessages({
  messages,
  isLoading = false,
  renderTrace,
  onCopy,
  rootClassName,
  contentClassName,
  streamSpeed = 50,
  fadeDuration = 200,
  segmentDelay = 30,
}: ChatMessagesProps) {
  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const [atBottom, setAtBottom] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState<ChatMessage | null>(
    null,
  );

  return (
    <div className={cn("h-full w-full relative flex flex-col", rootClassName)}>
      <Virtuoso
        ref={virtuosoRef}
        data={messages}
        style={{ height: "100%", width: "100%" }}
        className={cn("px-4 py-8", contentClassName)}
        followOutput={atBottom ? "auto" : false}
        atBottomStateChange={setAtBottom}
        itemContent={(index, message) => {
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
              <div className="flex flex-col pb-6">
                <Message
                  key={messageKey}
                  className="mx-auto w-full max-w-3xl justify-end px-4"
                >
                  <div className="flex w-full justify-end">
                    <MessageContent
                      className="text-foreground border-border/50 max-w-[85%] rounded-2xl border px-4 py-2.5 backdrop-blur-sm sm:max-w-[75%] whitespace-pre-wrap break-normal"
                      style={{
                        backgroundColor: "var(--color-background-primary-soft)",
                      }}
                    >
                      {message.content}
                    </MessageContent>
                  </div>
                </Message>
              </div>
            );
          }

          return (
            <div className="flex flex-col pb-6">
              <Message
                key={messageKey}
                className="mx-auto w-full max-w-3xl flex-col gap-2 px-4 items-start"
              >
                {renderTrace &&
                ((message.steps?.length ?? 0) > 0 || isStreaming)
                  ? renderTrace(message, isStreaming)
                  : null}

                <div className="group flex w-full flex-col gap-0">
                  <MessageContent
                    className={cn(
                      "text-foreground prose flex-1 rounded-lg bg-transparent p-0",
                      isStreaming && "whitespace-pre-wrap",
                    )}
                    markdown={true}
                    isStreaming={isStreaming}
                    streamSpeed={streamSpeed}
                    fadeDuration={fadeDuration}
                    segmentDelay={segmentDelay}
                  >
                    {typeof message.content === "string"
                      ? message.content
                      : JSON.stringify(message.content)}
                  </MessageContent>

                  {!isStreaming && (
                    <MessageActions className="-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                      {message.workflow_id && (
                        <MessageAction
                          tooltip="Debug Trace"
                          delayDuration={100}
                        >
                          <Button
                            variant="ghost"
                            size="icon"
                            className="rounded-full text-blue-500 hover:text-blue-600 hover:bg-blue-50/50"
                            onClick={() => setSelectedMessage(message)}
                            aria-label="View trace"
                          >
                            <Terminal className="size-4" />
                          </Button>
                        </MessageAction>
                      )}
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                          onClick={() => {
                            const contentStr =
                              typeof message.content === "string"
                                ? message.content
                                : JSON.stringify(message.content);
                            if (onCopy) {
                              onCopy(contentStr);
                            } else {
                              void navigator.clipboard.writeText(contentStr);
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
            </div>
          );
        }}
      />

      <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-4 pointer-events-none">
        <div className="pointer-events-auto">
          <ScrollButton
            className="shadow-sm"
            isAtBottom={atBottom}
            onClick={() =>
              virtuosoRef.current?.scrollToIndex({
                index: messages.length - 1,
                behavior: "smooth",
              })
            }
          />
        </div>
      </div>

      <Sheet
        open={!!selectedMessage}
        onOpenChange={(open) => !open && setSelectedMessage(null)}
      >
        <SheetContent
          side="right"
          className="sm:max-w-150 p-0 overflow-hidden border-l border-border/40 shadow-2xl"
        >
          {selectedMessage && (
            <TracePanel
              message={selectedMessage}
              isStreaming={false}
              isLoading={false}
              onWorkflowResponse={() => {}}
            />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
