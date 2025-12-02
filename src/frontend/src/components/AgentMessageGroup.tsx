"use client";

import React from "react";
import type { Message as MessageType } from "../api/types";
import { MessageBubble } from "./MessageBubble";
import { cn } from "@/lib/utils";

interface AgentMessageGroupProps {
  messages: MessageType[];
  groupId: string;
  isStreaming?: boolean;
  isReasoningStreaming?: boolean;
  currentReasoning?: string;
  onCancelStreaming?: () => void;
  className?: string;
}

/**
 * Groups consecutive messages from the same agent together
 * with a shared avatar/header and visual grouping
 */
export const AgentMessageGroup: React.FC<AgentMessageGroupProps> = ({
  messages,
  groupId,
  isStreaming = false,
  isReasoningStreaming = false,
  currentReasoning = "",
  onCancelStreaming,
  className,
}) => {
  if (messages.length === 0) return null;

  const firstMessage = messages[0];
  const agentName = firstMessage.author || "AI";
  const isMultipleMessages = messages.length > 1;

  return (
    <div
      className={cn("relative", isMultipleMessages && "pl-0", className)}
      data-group-id={groupId}
    >
      {/* Grouped messages container */}
      <div
        className={cn(
          "space-y-2",
          isMultipleMessages && "border-l-2 border-muted/30 pl-4 ml-4",
        )}
      >
        {messages.map((message, index) => {
          const isFirst = index === 0;
          const isLast = index === messages.length - 1;
          const showHeader = isFirst; // Only show avatar/name on first message

          return (
            <MessageBubble
              key={message.id || message.created_at}
              role={message.role}
              content={message.content}
              steps={message.steps}
              author={showHeader ? agentName : undefined}
              reasoning={isLast ? currentReasoning : undefined}
              isReasoningStreaming={isLast ? isReasoningStreaming : false}
              onCancelStreaming={isLast ? onCancelStreaming : undefined}
              isStreaming={isLast ? isStreaming : false}
              workflowPhase={message.workflowPhase}
              isWorkflowPlaceholder={message.isWorkflowPlaceholder}
              showAvatar={showHeader}
              isGrouped={isMultipleMessages}
              isFirstInGroup={isFirst}
              isLastInGroup={isLast}
            />
          );
        })}
      </div>
    </div>
  );
};

export default AgentMessageGroup;
