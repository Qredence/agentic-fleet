"use client";

import { useState, useMemo, memo } from "react";
import { Copy, Check, ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ChatStep } from "./ChatStep";
import type { Message as MessageType, ConversationStep } from "../api/types";
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageActions,
  MessageAction,
} from "./prompt-kit/message";
import { ChainOfThought } from "./prompt-kit/chain-of-thought";
import { ThinkingBar } from "./prompt-kit/thinking-bar";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "./prompt-kit/reasoning";
import { WorkflowEvents } from "./WorkflowEvents";
import { Loader } from "./prompt-kit/loader";
import {
  WORKFLOW_EVENT_TYPES,
  REASONING_STEP_TYPES,
  type WorkflowEventType,
  type ReasoningStepType,
} from "../lib/constants";

interface ChatMessageProps {
  /** Unique message ID for memoization optimization */
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  isFast?: boolean;
  latency?: string;
  steps?: MessageType["steps"];
  author?: string;
  agent_id?: string;
  reasoning?: string;
  isReasoningStreaming?: boolean;
  onCancelStreaming?: () => void;
  /** Whether the message is currently streaming */
  isStreaming?: boolean;
  /** Current workflow phase for shimmer display */
  workflowPhase?: string;
  showAvatar?: boolean;
  /** Whether this message is part of a group */
  isGrouped?: boolean;
  /** Whether this is the first message in a group */
  isFirstInGroup?: boolean;
  /** Whether this is the last message in a group */
  isLastInGroup?: boolean;
}

function categorizeSteps(steps: ConversationStep[]): {
  workflowEvents: ConversationStep[];
  reasoningSteps: ConversationStep[];
} {
  const workflowEvents: ConversationStep[] = [];
  const reasoningSteps: ConversationStep[] = [];

  for (const step of steps) {
    if (WORKFLOW_EVENT_TYPES.includes(step.type as WorkflowEventType)) {
      workflowEvents.push(step);
    } else if (REASONING_STEP_TYPES.includes(step.type as ReasoningStepType)) {
      reasoningSteps.push(step);
    }
  }

  return { workflowEvents, reasoningSteps };
}

export const ChatMessage = memo(function ChatMessage({
  id,
  role,
  content,
  isFast,
  latency,
  steps,
  author,
  agent_id,
  reasoning,
  isReasoningStreaming,
  onCancelStreaming,
  isStreaming = false,
  workflowPhase,
  showAvatar = true,
  isGrouped = false,
  isFirstInGroup = true,
  isLastInGroup = true,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";
  const isEmpty = !content || content.trim().length === 0;
  const isProcessing = isEmpty && !isUser;
  const displayName = author || agent_id || "AI";
  const avatarFallback = displayName.slice(0, 2).toUpperCase();

  // Categorize steps into workflow events and reasoning
  const { workflowEvents, reasoningSteps } = useMemo(() => {
    if (!steps || steps.length === 0) {
      return { workflowEvents: [], reasoningSteps: [] };
    }
    return categorizeSteps(steps);
  }, [steps]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // User message - simple bubble on the right
  if (isUser) {
    return (
      <Message className="justify-end">
        <MessageContent className="bg-primary text-primary-foreground max-w-[85%] rounded-3xl px-5 py-2.5 sm:max-w-[75%]">
          {content}
        </MessageContent>
      </Message>
    );
  }

  // Assistant message - full layout with avatar and features
  return (
    <Message className={cn(isGrouped && !isFirstInGroup ? "mt-1" : "")}>
      {showAvatar ? (
        <MessageAvatar src="" fallback={avatarFallback} alt={displayName} />
      ) : (
        <div className="w-8" /> // Spacer for alignment when avatar is hidden
      )}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Agent name header */}
        {showAvatar && (
          <div className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
            {displayName}
          </div>
        )}

        {/* Fast path indicator */}
        {isFast && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono uppercase tracking-wider">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Fast Path
            </span>
            <span>•</span>
            <span>{latency}</span>
          </div>
        )}

        {/* Workflow Events Section */}
        {(workflowEvents.length > 0 || (isStreaming && isProcessing)) && (
          <WorkflowEvents
            steps={workflowEvents}
            isStreaming={isStreaming}
            workflowPhase={workflowPhase}
          />
        )}

        {/* Chain of Thought Reasoning */}
        {reasoningSteps.length > 0 && (
          <div className="mb-2">
            <ChainOfThought>
              {reasoningSteps.map((step, index) => (
                <ChatStep key={step.id || index} step={step} />
              ))}
            </ChainOfThought>
          </div>
        )}

        {/* Extended Reasoning section for GPT-5 models */}
        {reasoning && (
          <Reasoning isStreaming={isReasoningStreaming} className="mb-2">
            <ReasoningTrigger className="text-xs text-muted-foreground">
              {isReasoningStreaming ? "Thinking..." : "View reasoning"}
            </ReasoningTrigger>
            <ReasoningContent markdown className="text-sm">
              {reasoning}
            </ReasoningContent>
          </Reasoning>
        )}

        {/* Main content or thinking indicator */}
        {isProcessing ? (
          <div className="flex items-center gap-3">
            <Loader variant="typing" size="sm" />
            <ThinkingBar
              text={
                isReasoningStreaming
                  ? "Reasoning..."
                  : workflowPhase || "Thinking"
              }
              onStop={onCancelStreaming}
              stopLabel="Stop"
            />
          </div>
        ) : (
          <MessageContent
            markdown
            id={id}
            className="prose prose-sm dark:prose-invert max-w-none bg-transparent p-0"
          >
            {content}
          </MessageContent>
        )}

        {/* Actions - show only for completed messages */}
        {!isProcessing && isLastInGroup && (
          <MessageActions className="opacity-0 group-hover:opacity-100 transition-opacity -ml-1">
            <MessageAction tooltip={copied ? "Copied!" : "Copy"}>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 rounded-full"
                onClick={handleCopy}
              >
                {copied ? (
                  <Check size={14} className="text-green-500" />
                ) : (
                  <Copy size={14} />
                )}
              </Button>
            </MessageAction>
            <MessageAction tooltip="Helpful">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 rounded-full"
              >
                <ThumbsUp size={14} />
              </Button>
            </MessageAction>
            <MessageAction tooltip="Not helpful">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 rounded-full"
              >
                <ThumbsDown size={14} />
              </Button>
            </MessageAction>
          </MessageActions>
        )}
      </div>
    </Message>
  );
});

// Export with both names for backwards compatibility
export const MessageBubble = ChatMessage;
