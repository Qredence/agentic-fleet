import React, { useState, useEffect, useRef, useCallback } from "react";
import { StreamingMessage } from "./StreamingMessage";
import { useChatStore } from "@/stores/chatStore";
import { performanceMonitor } from "@/utils/performance";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";

// Types
interface EnhancedMessageListProps {
  className?: string;
  conversationId?: string;
  showTimestamps?: boolean;
  showPerformance?: boolean;
  enableStreamingControls?: boolean;
  enableAutoScroll?: boolean;
  maxHeight?: string;
  onMessageAction?: (action: string, messageId: string) => void;
}

interface MessageGroup {
  id: string;
  type: "user" | "assistant" | "system";
  messages: Array<{
    id: string;
    content: string;
    timestamp: number;
    agentName?: string;
    streaming?: boolean;
  }>;
  agentName?: string;
}

// Icons
const RefreshIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const DownloadIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <polyline
      points="7 10 12 15 17 10"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <line
      x1="12"
      y1="15"
      x2="12"
      y2="3"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
    <path
      d="M12 1v6m0 6v6m4.22-13.22l4.24 4.24M1.54 1.54l4.24 4.24M21 12h-6m-6 0H3"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CopyIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <rect
      x="9"
      y="9"
      width="13"
      height="13"
      rx="2"
      ry="2"
      stroke="currentColor"
      strokeWidth="2"
    />
    <path
      d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const ThumbsUpIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M7 10v12m8-12v12m-4-6h4m-4 0l-4-4m4 4l4-4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const ThumbsDownIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M17 10v12m-8-12v12m4-6H9m4 0l4-4m-4 4l-4-4"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// Message Actions Component
const MessageActions: React.FC<{
  messageId: string;
  content: string;
  onAction?: (action: string, messageId: string) => void;
}> = ({ messageId, content, onAction }) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setIsCopied(true);
      toast.success("Message copied to clipboard");
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      toast.error("Failed to copy message");
    }
  }, [content]);

  const handleAction = useCallback(
    (action: string) => {
      onAction?.(action, messageId);
      toast.success(`${action} action triggered`);
    },
    [messageId, onAction],
  );

  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0"
            onClick={handleCopy}
          >
            {isCopied ? <span className="text-xs">✓</span> : <CopyIcon />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{isCopied ? "Copied!" : "Copy message"}</p>
        </TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0"
            onClick={() => handleAction("upvote")}
          >
            <ThumbsUpIcon />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Helpful</p>
        </TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0"
            onClick={() => handleAction("downvote")}
          >
            <ThumbsDownIcon />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Not helpful</p>
        </TooltipContent>
      </Tooltip>
    </div>
  );
};

// Enhanced Message List Component
export const EnhancedMessageList: React.FC<EnhancedMessageListProps> =
  React.memo(
    ({
      className,
      conversationId,
      showTimestamps = true,
      showPerformance = false,
      enableStreamingControls = true,
      enableAutoScroll = true,
      maxHeight = "calc(100vh - 200px)",
      onMessageAction,
    }) => {
      const { currentConversationId, messages, streaming } = useChatStore();
      const scrollAreaRef = useRef<HTMLDivElement>(null);
      const [showSettings, setShowSettings] = useState(false);
      const [autoScroll, setAutoScroll] = useState(enableAutoScroll);
      const [expandedMessages, setExpandedMessages] = useState<Set<string>>(
        new Set(),
      );

      const activeConversationId = conversationId || currentConversationId;
      const currentMessages = activeConversationId
        ? messages[activeConversationId] || []
        : [];

      // Group messages by user/assistant for better visual flow
      const messageGroups = React.useMemo(() => {
        const groups: MessageGroup[] = [];
        let currentGroup: MessageGroup | null = null;

        currentMessages.forEach((message, index) => {
          const role = message.role as "user" | "assistant" | "system";

          // Start new group if role changes
          if (!currentGroup || currentGroup.type !== role) {
            currentGroup = {
              id: `group-${index}`,
              type: role,
              messages: [],
              agentName: message.agentName,
            };
            groups.push(currentGroup);
          }

          currentGroup.messages.push({
            id: message.id,
            content: message.content,
            timestamp: message.timestamp || Date.now(),
            agentName: message.agentName,
            streaming: message.streaming,
          });
        });

        return groups;
      }, [currentMessages]);

      // Auto-scroll to bottom when new messages arrive
      useEffect(() => {
        if (autoScroll && scrollAreaRef.current) {
          const scrollElement = scrollAreaRef.current.querySelector(
            "[data-radix-scroll-area-viewport]",
          );
          if (scrollElement) {
            scrollElement.scrollTop = scrollElement.scrollHeight;
          }
        }
      }, [currentMessages.length, autoScroll]);

      // Track message interactions
      const handleMessageAction = useCallback(
        (action: string, messageId: string) => {
          onMessageAction?.(action, messageId);

          // Track performance for interactions
          performanceMonitor.trackInteraction(
            `message-${action}`,
            performance.now(),
          );

          // Update expanded state for detailed view
          if (action === "expand") {
            setExpandedMessages((prev) => new Set(prev).add(messageId));
          } else if (action === "collapse") {
            setExpandedMessages((prev) => {
              const newSet = new Set(prev);
              newSet.delete(messageId);
              return newSet;
            });
          }
        },
        [onMessageAction],
      );

      // Export conversation
      const handleExportConversation = useCallback(() => {
        if (!activeConversationId) return;

        const exportData = {
          conversationId: activeConversationId,
          messages: currentMessages,
          exportedAt: new Date().toISOString(),
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `conversation-${activeConversationId}.json`;
        a.click();
        URL.revokeObjectURL(url);

        toast.success("Conversation exported successfully");
      }, [activeConversationId, currentMessages]);

      // Refresh messages
      const handleRefresh = useCallback(() => {
        // This would trigger a refetch of messages from the server
        toast.info("Refreshing messages...");
      }, []);

      // Toggle message expansion
      const toggleMessageExpansion = useCallback((messageId: string) => {
        setExpandedMessages((prev) => {
          const newSet = new Set(prev);
          if (newSet.has(messageId)) {
            newSet.delete(messageId);
          } else {
            newSet.add(messageId);
          }
          return newSet;
        });
      }, []);

      return (
        <TooltipProvider delayDuration={100}>
          <div className={cn("flex flex-col h-full", className)}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="flex items-center gap-2">
                <h3 className="font-medium">Conversation</h3>
                {activeConversationId && (
                  <Badge variant="outline" className="text-xs">
                    {currentMessages.length} messages
                  </Badge>
                )}
                {streaming.isStreaming && (
                  <Badge variant="secondary" className="text-xs animate-pulse">
                    Streaming
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* Auto-scroll toggle */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant={autoScroll ? "default" : "outline"}
                      onClick={() => setAutoScroll(!autoScroll)}
                      className="h-8 px-3"
                    >
                      Auto-scroll: {autoScroll ? "On" : "Off"}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Toggle auto-scroll to new messages</p>
                  </TooltipContent>
                </Tooltip>

                {/* Performance toggle */}
                {showPerformance && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowSettings(!showSettings)}
                        className="h-8 w-8 p-0"
                      >
                        <SettingsIcon />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Show performance settings</p>
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Export */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleExportConversation}
                      className="h-8 w-8 p-0"
                      disabled={currentMessages.length === 0}
                    >
                      <DownloadIcon />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Export conversation</p>
                  </TooltipContent>
                </Tooltip>

                {/* Refresh */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleRefresh}
                      className="h-8 w-8 p-0"
                    >
                      <RefreshIcon />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Refresh messages</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>

            {/* Settings panel */}
            {showSettings && (
              <div className="p-4 border-b bg-muted/30 space-y-3">
                <h4 className="text-sm font-medium">Performance Settings</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <label className="block mb-1">Show timestamps</label>
                    <input
                      type="checkbox"
                      checked={showTimestamps}
                      disabled
                      className="rounded"
                    />
                  </div>
                  <div>
                    <label className="block mb-1">Show performance</label>
                    <input
                      type="checkbox"
                      checked={showPerformance}
                      disabled
                      className="rounded"
                    />
                  </div>
                  <div>
                    <label className="block mb-1">Streaming controls</label>
                    <input
                      type="checkbox"
                      checked={enableStreamingControls}
                      disabled
                      className="rounded"
                    />
                  </div>
                  <div>
                    <label className="block mb-1">Auto-scroll</label>
                    <input
                      type="checkbox"
                      checked={autoScroll}
                      onChange={(e) => setAutoScroll(e.target.checked)}
                      className="rounded"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <ScrollArea
              ref={scrollAreaRef}
              className="flex-1"
              style={{ maxHeight }}
            >
              <div className="p-4 space-y-6">
                {messageGroups.map((group) => (
                  <div
                    key={group.id}
                    className={cn(
                      "relative",
                      group.type === "assistant" &&
                        "bg-muted/20 rounded-lg p-4",
                      group.type === "user" && "flex justify-end",
                      group.type === "system" &&
                        "text-center text-xs text-muted-foreground py-2",
                    )}
                  >
                    {/* System messages */}
                    {group.type === "system" && (
                      <div className="italic">{group.messages[0].content}</div>
                    )}

                    {/* User messages */}
                    {group.type === "user" && (
                      <div className="max-w-3xl">
                        {group.messages.map((message) => (
                          <div key={message.id} className="group relative">
                            <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-sm p-3 shadow-sm">
                              <div className="text-sm whitespace-pre-wrap">
                                {message.content}
                              </div>
                            </div>

                            {/* User message actions */}
                            <div className="absolute top-0 right-full mr-2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                              <MessageActions
                                messageId={message.id}
                                content={message.content}
                                onAction={handleMessageAction}
                              />
                            </div>

                            {showTimestamps && (
                              <div className="text-xs text-muted-foreground mt-1 text-right">
                                {new Date(
                                  message.timestamp,
                                ).toLocaleTimeString()}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Assistant messages */}
                    {group.type === "assistant" && (
                      <div className="space-y-4">
                        {group.messages.map((message) => (
                          <div key={message.id} className="group">
                            <StreamingMessage
                              messageId={message.id}
                              conversationId={activeConversationId!}
                              role="assistant"
                              initialContent={message.content}
                              agentName={group.agentName}
                              showTimestamps={showTimestamps}
                              showPerformance={showPerformance}
                              enableInteraction={enableStreamingControls}
                            />

                            {/* Assistant message actions */}
                            <div className="flex items-center justify-between mt-2">
                              <MessageActions
                                messageId={message.id}
                                content={message.content}
                                onAction={handleMessageAction}
                              />

                              {expandedMessages.has(message.id) && (
                                <div className="text-xs text-muted-foreground">
                                  Message ID: {message.id}
                                </div>
                              )}
                            </div>

                            {message.streaming && (
                              <div className="mt-2">
                                <Progress value={75} className="h-1" />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {/* Empty state */}
                {currentMessages.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    <p>No messages yet</p>
                    <p className="text-sm mt-1">
                      Start a conversation to see messages here
                    </p>
                  </div>
                )}

                {/* Streaming indicator at bottom */}
                {streaming.isStreaming && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                    <span>
                      {streaming.agentName || "Assistant"} is typing...
                    </span>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </TooltipProvider>
      );
    },
  );

EnhancedMessageList.displayName = "EnhancedMessageList";
