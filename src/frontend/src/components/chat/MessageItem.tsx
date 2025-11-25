/**
 * MessageItem Component
 * Displays a single message with avatar, content, and optional reasoning
 */

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { Button } from "@openai/apps-sdk-ui/components/Button";
import { User, Bot, ChevronDown, ChevronRight } from "lucide-react";
import type { Message } from "../../lib/api/chatApi";

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
  streamingAgentId?: string;
}

export function MessageItem({
  message,
  isStreaming = false,
  streamingAgentId,
}: MessageItemProps) {
  const [showReasoning, setShowReasoning] = useState(false);
  const isUser = message.role === "user";

  return (
    <div
      className={`group flex gap-4 py-6 px-4 ${isUser ? "bg-surface" : "bg-transparent"}`}
    >
      {/* Avatar */}
      <div className="shrink-0">
        <div className="size-10 rounded-full bg-surface border border-default flex items-center justify-center ">
          {isUser ? <User className="size-5" /> : <Bot className="size-5" />}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Role */}
        <div className="text-xs font-medium text-secondary uppercase tracking-wide">
          {isUser ? "You" : "Assistant"}
        </div>

        {/* Message content */}
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
            components={{
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              code: ({ inline, className, children, ...props }: any) => {
                if (inline) {
                  return (
                    <code
                      className="rounded bg-surface-alt px-1.5 py-0.5 text-xs font-mono"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
          )}
          {isStreaming && streamingAgentId && (
            <div className="text-xs text-tertiary mt-1">
              Streaming from {streamingAgentId}
            </div>
          )}
        </div>

        {/* Reasoning (if available) */}
        {message.reasoning && (
          <div className="mt-3">
            <Button
              variant="ghost"
              color="secondary"
              size="sm"
              onClick={() => setShowReasoning(!showReasoning)}
              className="text-xs"
            >
              {showReasoning ? (
                <ChevronDown className="size-3" />
              ) : (
                <ChevronRight className="size-3" />
              )}
              Reasoning
            </Button>
            {showReasoning && (
              <div className="mt-2 rounded-lg border border-default bg-surface-alt p-3 text-sm text-secondary">
                {message.reasoning}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className="text-xs text-tertiary">
          {new Date(message.created_at * 1000).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
