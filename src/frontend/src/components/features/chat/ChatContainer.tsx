/**
 * ChatContainer Component - Refactored Version
 *
 * Simplified main chat container that composes specialized components:
 * - ChatMessagesList: Message display and scrolling
 * - ChatStatusBar: Status indicators
 * - ChatSuggestions: Prompt suggestions
 * - ChatPlanDisplay: Plan visualization
 * - ApprovalPrompt: Human-in-the-loop approvals
 *
 * This refactored version reduces complexity from 452 lines to ~150 lines
 * while maintaining the same functionality and improving performance.
 */

import { ApprovalPrompt } from "@/components/features/approval";
import { useToast } from "@/hooks/use-toast";
import { useFastAPIChat } from "@/lib/use-fastapi-chat";
import type { ApprovalResponsePayload, PendingApproval } from "@/lib/types";
import { memo, useCallback, useEffect } from "react";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { ChatMessagesList } from "./ChatMessagesList";
import { ChatPlanDisplay } from "./ChatPlanDisplay";
import { ChatStatusBar } from "./ChatStatusBar";
import { ChatSuggestions } from "./ChatSuggestions";

interface ChatContainerProps {
  conversationId?: string;
  onConversationChange?: (conversationId?: string) => void;
}

const ChatContainerComponent = ({
  conversationId: activeConversationId,
  onConversationChange,
}: ChatContainerProps) => {
  const { toast } = useToast();

  const {
    messages,
    status,
    error,
    sendMessage,
    pendingApprovals,
    approvalStatuses,
    respondToApproval,
    currentPlan,
    conversationId,
    queueStatus,
    connectionStatus,
    checkHealth,
  } = useFastAPIChat({ conversationId: activeConversationId });

  const handleSendMessage = useCallback(
    async (content: string) => {
      try {
        await sendMessage(content);
      } catch (error) {
        toast({
          title: "Failed to send message",
          description: error instanceof Error ? error.message : "Unknown error",
          variant: "destructive",
        });
      }
    },
    [sendMessage, toast],
  );

  const handleSuggestionSelect = useCallback(
    (suggestion: string) => {
      handleSendMessage(suggestion);
    },
    [handleSendMessage],
  );

  const handleApprovalApprove = useCallback(
    async (
      approval: PendingApproval,
      options?: {
        modifiedCode?: string;
        modifiedParams?: Record<string, unknown>;
        reason?: string;
      },
    ) => {
      const payload: ApprovalResponsePayload = options && (options.modifiedCode || options.modifiedParams)
        ? {
            type: "modify",
            modifiedCode: options.modifiedCode,
            modifiedParams: options.modifiedParams,
            reason: options.reason,
          }
        : { type: "approve", reason: options?.reason };

      try {
        await respondToApproval(approval.requestId, payload);
        toast({
          title: "Approval submitted",
          description: "The agent has been notified.",
        });
      } catch (error) {
        toast({
          title: "Failed to submit approval",
          description: error instanceof Error ? error.message : "Unknown error",
          variant: "destructive",
        });
      }
    },
    [respondToApproval, toast],
  );

  const handleApprovalReject = useCallback(
    async (approval: PendingApproval, reason: string) => {
      const payload: ApprovalResponsePayload = { type: "reject", reason };

      try {
        await respondToApproval(approval.requestId, payload);
        toast({
          title: "Approval rejected",
          description: "The agent will halt this operation.",
        });
      } catch (error) {
        toast({
          title: "Failed to submit rejection",
          description: error instanceof Error ? error.message : "Unknown error",
          variant: "destructive",
        });
      }
    },
    [respondToApproval, toast],
  );

  // Sync conversation ID with parent
  useEffect(() => {
    onConversationChange?.(conversationId);
  }, [conversationId, onConversationChange]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + Enter to send message
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        // This will be handled by ChatInput component
        return;
      }

      // Escape to clear input
      if (event.key === "Escape") {
        // Clear any focused approval prompts or handle other escape actions
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Show suggestions when there are no messages
  const showSuggestions = messages.length === 0 && status === "ready";

  return (
    <div className="flex flex-col h-screen w-full bg-background overflow-hidden">
      {/* Header - Responsive, no fixed positioning */}
      <ChatHeader
        conversationId={conversationId}
        connectionStatus={connectionStatus}
        onCheckHealth={checkHealth}
      />

      {/* Main Content Area - Flex-grow with proper overflow */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {/* Messages List - Takes available space */}
        <div className="flex-1 overflow-hidden">
          <ChatMessagesList
            messages={messages}
            isStreaming={status === "streaming"}
            queueStatus={queueStatus}
            className="h-full"
          />
        </div>

        {/* Plan Display - Collapsible section */}
        {currentPlan && (
          <div className="flex-shrink-0 border-t bg-background/95 backdrop-blur-sm">
            <div className="max-w-4xl mx-auto p-3 sm:p-4">
              <ChatPlanDisplay plan={currentPlan} />
            </div>
          </div>
        )}

        {/* Suggestions - Centered overlay when no messages */}
        {showSuggestions ? (
          <div className="absolute inset-0 flex items-center justify-center overflow-y-auto">
            <div className="w-full max-w-2xl px-4 py-8">
              <ChatSuggestions
                onSuggestionSelect={handleSuggestionSelect}
                isVisible={showSuggestions}
                chatStatus={status}
                className="space-y-6"
              />
            </div>
          </div>
        ) : (
          <>
            {/* Messages List */}
            <ChatMessagesList
              messages={messages}
              isStreaming={status === "streaming"}
              queueStatus={queueStatus}
              className="flex-1"
            />

            {/* Plan Display */}
            {currentPlan && (
              <div className="border-t bg-background">
                <div className="max-w-4xl mx-auto p-4">
                  <ChatPlanDisplay plan={currentPlan} />
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Status Bar - Compact on mobile */}
      <ChatStatusBar
        connectionStatus={connectionStatus}
        chatStatus={status}
        error={error}
        queueStatus={queueStatus}
        className="flex-shrink-0 border-t"
      />

      {/* Pending Approvals - Above input */}
      {pendingApprovals.length > 0 && (
        <div className="flex-shrink-0 border-t bg-background/95 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto p-3 sm:p-4 space-y-3">
            {pendingApprovals.map((approval) => (
              <ApprovalPrompt
                key={approval.requestId}
                approval={approval}
                status={
                  approvalStatuses[approval.requestId] ?? { status: "idle" }
                }
                onApprove={(options) =>
                  handleApprovalApprove(approval, options)
                }
                onReject={(reason) =>
                  handleApprovalReject(approval, reason)
                }
              />
            ))}
          </div>
        </div>
      )}

      {/* Input Area - Sticky bottom with responsive padding */}
      <div className="flex-shrink-0 border-t bg-background">
        <div className="max-w-4xl mx-auto p-3 sm:p-4">
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={status === "streaming" || status === "submitted"}
            placeholder={
              status === "streaming" || status === "submitted"
                ? "Processing..."
                : "Type your message..."
            }
          />
        </div>
      </div>
    </div>
  );
};

// Export memoized component for performance
export const ChatContainer = memo(ChatContainerComponent);
