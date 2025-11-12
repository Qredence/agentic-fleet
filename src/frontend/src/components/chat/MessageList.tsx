import { useMemo } from "react";
import type { ChatMessage } from "@/types/chat";
import { MessageListItem } from "./MessageListItem";

interface MessageListProps {
  messages: ChatMessage[];
  currentStreamingMessage?: string;
  currentStreamingMessageId?: string;
  currentStreamingTimestamp?: number;
  currentAgentId?: string;
  currentReasoningContent?: string;
  currentReasoningStreaming?: boolean;
}

/** Renders the chat message list with memoized streaming append and item memoization */
export function MessageList({
  messages,
  currentStreamingMessage,
  currentStreamingMessageId,
  currentStreamingTimestamp,
  currentAgentId,
  currentReasoningContent,
  currentReasoningStreaming,
}: MessageListProps) {
  // useMemo recalculates on every currentStreamingMessage change for real-time updates
  // This ensures the streaming message content updates immediately in the UI
  const allMessages = useMemo(() => {
    if (!currentStreamingMessage) {
      return messages;
    }
    const streamingId = currentStreamingMessageId ?? "streaming-current";
    return [
      ...messages,
      {
        id: streamingId,
        role: "assistant" as const,
        content: currentStreamingMessage,
        agentId: currentAgentId,
        createdAt: currentStreamingTimestamp ?? Date.now(),
      },
    ];
  }, [
    messages,
    currentStreamingMessage,
    currentStreamingMessageId,
    currentStreamingTimestamp,
    currentAgentId,
  ]);

  return (
    <div className="space-y-12">
      {allMessages.map((message, index) => {
        const isStreamingMessage =
          Boolean(currentStreamingMessageId) &&
          message.id === currentStreamingMessageId;
        const isLastMessage = index === allMessages.length - 1;

        return (
          <div key={message.id} data-testid={`message-item-${message.id}`}>
            <MessageListItem
              message={message}
              isStreamingMessage={isStreamingMessage}
              isLastMessage={isLastMessage}
              currentReasoningContent={currentReasoningContent}
              currentReasoningStreaming={currentReasoningStreaming}
            />
          </div>
        );
      })}
    </div>
  );
}
