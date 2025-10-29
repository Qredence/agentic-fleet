/**
 * ChatMessagesList Component
 *
 * Handles the display and scrolling of chat messages:
 * - Message rendering with timestamps
 * - Scroll management and auto-scroll
 * - "Scroll to latest" functionality
 * - Performance optimizations with React.memo
 */

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatMessage } from "./ChatMessage";
import { Loader2 } from "lucide-react";
import { Loader, TypingLoader } from "@/components/ui/prompt-kit";
import {
  ChatContainerRoot,
  ChatContainerContent,
  ChatContainerScrollAnchor,
  ScrollButton,
} from "@/components/ui/prompt-kit";
import type { Message, QueueStatus } from "@/lib/types";

interface DisplayMessage extends Message {
  receivedAt: string;
}

interface ChatMessagesListProps {
  messages: Message[];
  isStreaming?: boolean;
  queueStatus?: QueueStatus;
  onScrollToLatest?: () => void;
  className?: string;
}

const ChatMessagesListComponent = ({
  messages,
  isStreaming = false,
  queueStatus,
  className = "",
}: ChatMessagesListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messageTimestampsRef = useRef<Map<string, string>>(new Map());
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [displayMessages, setDisplayMessages] = useState<DisplayMessage[]>([]);

  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      }),
    []
  );

  // Memoize display messages with timestamps
  const messagesWithTimestamps = useMemo(() => {
    return messages.map((message) => {
      let receivedAt = messageTimestampsRef.current.get(message.id);

      if (!receivedAt) {
        receivedAt = timeFormatter.format(new Date());
        messageTimestampsRef.current.set(message.id, receivedAt);
      }

      return {
        ...message,
        receivedAt,
      } as DisplayMessage;
    });
  }, [messages, timeFormatter]);

  // Update display messages when messages change
  useEffect(() => {
    setDisplayMessages(messagesWithTimestamps);
  }, [messagesWithTimestamps]);

  const scrollToLatest = useCallback(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
          setIsAtBottom(true);
        }
      });
    });
  }, []);

  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    const threshold = 120;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    setIsAtBottom(distanceFromBottom <= threshold);
  }, []);

  // Auto-scroll when new messages arrive and user is at bottom
  useEffect(() => {
    if (isAtBottom && messages.length > 0) {
      scrollToLatest();
    }
  }, [messages, isAtBottom, scrollToLatest]);

  // Set up scroll listener
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    container.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll]);

  // Render queue status if active
  const renderQueueStatus = () => {
    if (!queueStatus || queueStatus.phase === "finished") {
      return null;
    }

    return (
      <div className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Queue Status: {queueStatus.phase}</span>
        <Badge variant="secondary" className="text-xs">
          {queueStatus.inflight}/{queueStatus.maxParallel} active
        </Badge>
        {queueStatus.queued > 0 && (
          <Badge variant="outline" className="text-xs">
            {queueStatus.queued} queued
          </Badge>
        )}
      </div>
    );
  };

  return (
    <div className={`flex flex-col h-full relative ${className}`}>
      {renderQueueStatus()}

      <ChatContainerRoot className="flex-1 overflow-hidden">
        <ChatContainerContent className="space-y-3 sm:space-y-4 p-3 sm:p-4">
          {displayMessages.map((message, index) => (
            <ChatMessage
              key={message.id}
              message={message}
              isStreaming={isStreaming && index === displayMessages.length - 1}
            />
          ))}

          {isStreaming && (
            <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-muted/30 rounded-lg">
              <TypingLoader size="sm" />
              <span className="text-xs sm:text-sm text-muted-foreground">Agent is thinking...</span>
              <Loader variant="pulse-dot" size="sm" />
            </div>
          )}

          <ChatContainerScrollAnchor ref={messagesEndRef} />
        </ChatContainerContent>

        {/* Enhanced scroll button - positioned for mobile accessibility */}
        <div className="absolute bottom-3 right-3 sm:bottom-4 sm:right-4">
          <ScrollButton className="shadow-lg h-10 w-10 sm:h-12 sm:w-12" />
        </div>
      </ChatContainerRoot>
    </div>
  );
};

// Export memoized component
export const ChatMessagesList = memo(ChatMessagesListComponent);