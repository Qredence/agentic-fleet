import React, { useState, useEffect, useRef } from "react";
import { Message, MessageContent } from "@/components/prompt-kit/message";
import { useChatStore } from "@/stores/chatStore";
import { performanceMonitor, usePerformanceMonitor } from "@/utils/performance";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Types
interface StreamingMessageProps {
  messageId: string;
  conversationId: string;
  role: "user" | "assistant" | "system";
  initialContent?: string;
  agentName?: string;
  avatar?: string;
  showTimestamp?: boolean;
  showPerformance?: boolean;
  enableInteraction?: boolean;
  className?: string;
}

interface StreamingChunk {
  content: string;
  timestamp: number;
  delay: number;
}

interface AgentAvatarProps {
  agentName?: string;
  isStreaming?: boolean;
  avatar?: string;
  size?: "sm" | "md" | "lg";
}

// Icons
const BotIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M12 8V4H8"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M16 4h2a2 2 0 0 1 2 2v4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M20 14v4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M14 14h4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle
      cx="17"
      cy="17"
      r="1"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const UserIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle
      cx="12"
      cy="7"
      r="4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const TypingIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <circle cx="5" cy="12" r="1" fill="currentColor">
      <animate
        attributeName="r"
        values="1;2;1"
        dur="1.5s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="opacity"
        values="1;0.5;1"
        dur="1.5s"
        repeatCount="indefinite"
      />
    </circle>
    <circle cx="12" cy="12" r="1" fill="currentColor">
      <animate
        attributeName="r"
        values="1;2;1"
        dur="1.5s"
        begin="0.2s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="opacity"
        values="1;0.5;1"
        dur="1.5s"
        begin="0.2s"
        repeatCount="indefinite"
      />
    </circle>
    <circle cx="19" cy="12" r="1" fill="currentColor">
      <animate
        attributeName="r"
        values="1;2;1"
        dur="1.5s"
        begin="0.4s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="opacity"
        values="1;0.5;1"
        dur="1.5s"
        begin="0.4s"
        repeatCount="indefinite"
      />
    </circle>
  </svg>
);

const PauseIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <rect x="6" y="4" width="4" height="16" fill="currentColor" />
    <rect x="14" y="4" width="4" height="16" fill="currentColor" />
  </svg>
);

const StopIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <rect x="6" y="6" width="12" height="12" fill="currentColor" />
  </svg>
);

// Agent Avatar Component
const AgentAvatar: React.FC<AgentAvatarProps> = ({
  agentName,
  isStreaming,
  avatar,
  size = "md",
}) => {
  const sizeClasses = {
    sm: "w-6 h-6",
    md: "w-8 h-8",
    lg: "w-10 h-10",
  };

  if (avatar) {
    return (
      <div className={cn("rounded-full overflow-hidden", sizeClasses[size])}>
        <img
          src={avatar}
          alt={agentName}
          className="w-full h-full object-cover"
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full border-2 transition-colors",
        sizeClasses[size],
        isStreaming
          ? "bg-primary text-primary-foreground border-primary"
          : "bg-muted text-muted-foreground border-muted-foreground",
      )}
    >
      {isStreaming ? (
        <TypingIcon className="animate-pulse" />
      ) : agentName ? (
        <BotIcon />
      ) : (
        <UserIcon />
      )}
    </div>
  );
};

// Streaming Message Component
export const StreamingMessage: React.FC<StreamingMessageProps> = React.memo(
  ({
    messageId,
    conversationId,
    role,
    initialContent = "",
    agentName,
    avatar,
    showTimestamp = true,
    showPerformance = true,
    enableInteraction = true,
    className,
  }) => {
    const { streaming, messages } = useChatStore();
    const perf = usePerformanceMonitor();

    // Local state
    const [displayedContent, setDisplayedContent] = useState(initialContent);
    const [chunkHistory, setChunkHistory] = useState<StreamingChunk[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [typingSpeed, setTypingSpeed] = useState(30); // ms per character
    const [showMetrics, setShowMetrics] = useState(false);

    // Refs
    const messageRef = useRef<HTMLDivElement>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const animationRef = useRef<number | null>(null);

    // Get the current message from store
    const currentMessage = messages[conversationId]?.find(
      (msg) => msg.id === messageId,
    );
    const isStreaming =
      streaming.isStreaming && streaming.currentMessageId === messageId;

    // Handle streaming content updates
    useEffect(() => {
      if (currentMessage && currentMessage.content !== displayedContent) {
        const newContent = currentMessage.content;
        const timestamp = Date.now();

        // Calculate chunk delay
        const delay =
          chunkHistory.length > 0
            ? timestamp - chunkHistory[chunkHistory.length - 1].timestamp
            : 0;

        const newChunk: StreamingChunk = {
          content: newContent,
          timestamp,
          delay,
        };

        setChunkHistory((prev) => [...prev, newChunk]);

        if (isStreaming) {
          // Animate typing effect
          setIsTyping(true);
          animateTyping(displayedContent, newContent);
        } else {
          // Show content immediately if not streaming
          setDisplayedContent(newContent);
          setIsTyping(false);
        }
      }
    }, [
      currentMessage?.content,
      displayedContent,
      isStreaming,
      chunkHistory.length,
    ]);

    // Typing animation
    const animateTyping = (from: string, to: string) => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      if (from === to) {
        setIsTyping(false);
        return;
      }

      let currentIndex = from.length;
      const targetContent = to;

      const typeNextChar = () => {
        if (currentIndex < targetContent.length) {
          setDisplayedContent(targetContent.slice(0, currentIndex + 1));
          currentIndex++;

          typingTimeoutRef.current = setTimeout(typeNextChar, typingSpeed);
        } else {
          setIsTyping(false);
        }
      };

      typeNextChar();
    };

    // Auto-scroll to message when new content arrives
    useEffect(() => {
      if (messageRef.current && isStreaming) {
        // Smooth scroll to the message
        messageRef.current.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }
    }, [displayedContent, isStreaming]);

    // Performance metrics calculation
    const performanceMetrics = React.useMemo(() => {
      if (chunkHistory.length === 0) return null;

      const totalDuration =
        chunkHistory[chunkHistory.length - 1].timestamp -
        chunkHistory[0].timestamp;
      const totalChars = chunkHistory[chunkHistory.length - 1].content.length;
      const averageDelay =
        chunkHistory.reduce((sum, chunk, index) => {
          return index > 0 ? sum + chunk.delay : sum;
        }, 0) / Math.max(1, chunkHistory.length - 1);

      const chunksPerSecond =
        chunkHistory.length > 1
          ? (chunkHistory.length - 1) / (totalDuration / 1000)
          : 0;
      const charsPerSecond =
        totalChars > 0 ? totalChars / (totalDuration / 1000) : 0;

      return {
        totalDuration,
        totalChars,
        chunkCount: chunkHistory.length,
        averageDelay,
        chunksPerSecond,
        charsPerSecond,
      };
    }, [chunkHistory]);

    // Handle streaming controls
    const handlePauseStreaming = async () => {
      // This would integrate with the parent component's streaming control
      console.log("Pause streaming for message:", messageId);
    };

    const handleStopStreaming = async () => {
      // This would integrate with the parent component's streaming control
      console.log("Stop streaming for message:", messageId);
    };

    // Format timestamp
    const formatTimestamp = (timestamp: number) => {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    };

    // Calculate message age
    const messageAge = currentMessage
      ? Math.floor(
          (Date.now() - (currentMessage.timestamp || Date.now())) / 1000,
        )
      : 0;

    return (
      <TooltipProvider delayDuration={100}>
        <div
          ref={messageRef}
          className={cn(
            "group relative transition-all duration-200",
            isStreaming && "animate-pulse-soft",
            className,
          )}
        >
          <Message>
            <div className="flex gap-3">
              {/* Avatar */}
              <div className="flex-shrink-0 mt-1">
                <AgentAvatar
                  agentName={agentName}
                  isStreaming={isStreaming}
                  avatar={avatar}
                  size="md"
                />
              </div>

              {/* Message content */}
              <div className="flex-1 min-w-0">
                {/* Header */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">
                    {agentName || (role === "user" ? "You" : "Assistant")}
                  </span>

                  {/* Streaming indicator */}
                  {isStreaming && (
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <span className="text-xs text-green-600 dark:text-green-400">
                        Streaming
                      </span>
                    </div>
                  )}

                  {/* Typing indicator */}
                  {isTyping && (
                    <div className="flex items-center gap-1">
                      <TypingIcon />
                      <span className="text-xs text-muted-foreground">
                        Typing
                      </span>
                    </div>
                  )}

                  {/* Timestamp */}
                  {showTimestamp && currentMessage?.timestamp && (
                    <span className="text-xs text-muted-foreground ml-auto">
                      {formatTimestamp(currentMessage.timestamp)}
                      {messageAge < 60 && ` (${messageAge}s ago)`}
                    </span>
                  )}
                </div>

                {/* Content */}
                <div
                  className={cn(
                    "relative",
                    isStreaming &&
                      "after:content-[''] after:absolute after:bottom-0 after:left-0 after:h-px after:w-full after:bg-gradient-to-r after:from-transparent after:via-primary after:to-transparent after:animate-pulse",
                  )}
                >
                  <MessageContent markdown>
                    {displayedContent || (isStreaming ? "..." : "")}
                  </MessageContent>

                  {/* Cursor for streaming */}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />
                  )}
                </div>

                {/* Performance metrics */}
                {showPerformance && performanceMetrics && isStreaming && (
                  <div className="mt-2 p-2 bg-muted/50 rounded-lg border">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium">Performance</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-4 w-4 p-0 ml-auto"
                        onClick={() => setShowMetrics(!showMetrics)}
                      >
                        {showMetrics ? "−" : "+"}
                      </Button>
                    </div>

                    {showMetrics && (
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          Duration:{" "}
                          {(performanceMetrics.totalDuration / 1000).toFixed(1)}
                          s
                        </div>
                        <div>Chunks: {performanceMetrics.chunkCount}</div>
                        <div>Chars: {performanceMetrics.totalChars}</div>
                        <div>
                          Speed: {performanceMetrics.charsPerSecond.toFixed(0)}{" "}
                          chars/s
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Streaming controls */}
                {enableInteraction && isStreaming && (
                  <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs"
                          onClick={handlePauseStreaming}
                        >
                          <PauseIcon className="w-3 h-3" />
                          Pause
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Pause streaming</p>
                      </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs"
                          onClick={handleStopStreaming}
                        >
                          <StopIcon className="w-3 h-3" />
                          Stop
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Stop streaming</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                )}

                {/* Agent info badge */}
                {agentName && role === "assistant" && (
                  <div className="mt-2">
                    <Badge variant="secondary" className="text-xs">
                      {agentName}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </Message>
        </div>
      </TooltipProvider>
    );
  },
);

StreamingMessage.displayName = "StreamingMessage";
