/**
 * MessageList Component
 * Scrollable list of messages with auto-scroll to bottom
 */

import { useEffect, useRef } from "react";
import { MessageItem } from "./MessageItem";
import type { Message } from "../../lib/api/chatApi";
import { ReasoningDisplay } from "./ReasoningDisplay";

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  orchestratorThought?: string;
  streamingAgentId?: string;
  streamingReasoning?: string;
  isStreaming?: boolean;
}

export function MessageList({
  messages,
  streamingContent,
  orchestratorThought,
  streamingAgentId,
  streamingReasoning,
  isStreaming = false,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, streamingContent, isStreaming]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto messages-container"
    >
      {/* Empty state */}
      {messages.length === 0 && !isStreaming && (
        <div className="flex h-full items-center justify-center">
          <div className="text-center space-y-3">
            <div className="text-6xl">💬</div>
            <h2 className="heading-lg">Start a conversation</h2>
            <p className="text-secondary text-sm max-w-sm">
              Ask me anything! I'm here to help you with your questions.
            </p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="divide-y divide-subtle">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}

        {/* Orchestrator thought */}
        {orchestratorThought && (
          <div className="py-4 px-4 bg-surface-alt">
            <div className="flex items-start gap-3">
              <div className="shrink-0">
                <div className="size-6 rounded-full bg-primary/20 flex items-center justify-center">
                  <div className="size-2 rounded-full bg-primary animate-pulse" />
                </div>
              </div>
              <div className="text-sm text-secondary italic">
                {orchestratorThought}
              </div>
            </div>
          </div>
        )}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <MessageItem
            message={{
              id: "streaming",
              role: "assistant",
              content: streamingContent,
              created_at: Date.now() / 1000,
            }}
            isStreaming={true}
            streamingAgentId={streamingAgentId}
          />
        )}

        {/* Streaming reasoning */}
        {isStreaming && streamingReasoning && (
          <div className="px-4 pb-4">
            <ReasoningDisplay
              content={streamingReasoning}
              isStreaming
              defaultOpen
              triggerText="Model reasoning"
            />
          </div>
        )}
      </div>

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}
