import { useState, useMemo } from "react";
import { Copy, Check } from "lucide-react";
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
import { Loader2 } from "lucide-react";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "./prompt-kit/reasoning";
import { WorkflowEvents } from "./WorkflowEvents";
import {
  WORKFLOW_EVENT_TYPES,
  REASONING_STEP_TYPES,
  type WorkflowEventType,
  type ReasoningStepType,
} from "../lib/constants";

interface MessageBubbleProps {
  /** Unique message ID for memoization optimization */
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  isFast?: boolean;
  latency?: string;
  steps?: MessageType["steps"];
  author?: string;
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
    // error steps are handled separately in the UI
  }

  return { workflowEvents, reasoningSteps };
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  id,
  role,
  content,
  isFast,
  latency,
  steps,
  author,
  reasoning,
  isReasoningStreaming,
  onCancelStreaming,
  isStreaming = false,
  workflowPhase,
  showAvatar = true,
  isGrouped = false,
  isFirstInGroup = true,
  isLastInGroup = true,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";
  const isEmpty = !content || content.trim().length === 0;
  const isProcessing = isEmpty && !isUser;
  const displayName = author || "AI";
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

  if (isUser) {
    return (
      <Message className="justify-end">
        <MessageContent className="bg-primary text-primary-foreground">
          {content}
        </MessageContent>
      </Message>
    );
  }

  return (
    <Message className={isGrouped && !isFirstInGroup ? "mt-1" : ""}>
      {showAvatar ? (
        <MessageAvatar src="" fallback={avatarFallback} alt={displayName} />
      ) : (
        <div className="w-8" /> // Spacer for alignment when avatar is hidden
      )}
      <div className="flex-1 min-w-0 space-y-2">
        {showAvatar && (
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {displayName}
          </div>
        )}
        {isFast && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono uppercase tracking-wider">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              Fast Path
            </span>
            <span>•</span>
            <span>{latency}</span>
          </div>
        )}

        {/* Workflow Events Section - uses Steps component */}
        {(workflowEvents.length > 0 || (isStreaming && isProcessing)) && (
          <WorkflowEvents
            steps={workflowEvents}
            isStreaming={isStreaming}
            workflowPhase={workflowPhase}
          />
        )}

        {/* Chain of Thought Reasoning - only for actual AI reasoning traces */}
        {reasoningSteps.length > 0 && (
          <div className="mb-2">
            <ChainOfThought>
              {reasoningSteps.map((step, index) => (
                <ChatStep key={step.id || index} step={step} />
              ))}
            </ChainOfThought>
          </div>
        )}

        {/* Reasoning section for GPT-5 models */}
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

        {isProcessing ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 size={14} className="animate-spin" />
            <span>
              {isReasoningStreaming
                ? "Reasoning..."
                : workflowPhase || "Processing..."}
            </span>
            {onCancelStreaming && (
              <button
                onClick={onCancelStreaming}
                className="ml-2 text-xs hover:text-foreground border-b border-dotted border-muted-foreground/50"
              >
                Stop
              </button>
            )}
          </div>
        ) : (
          <MessageContent markdown id={id}>
            {content}
          </MessageContent>
        )}

        {!isProcessing && isLastInGroup && (
          <MessageActions>
            <MessageAction tooltip={copied ? "Copied!" : "Copy"}>
              <button
                onClick={handleCopy}
                className="p-1 hover:text-foreground transition-colors"
              >
                {copied ? (
                  <Check size={14} className="text-green-500" />
                ) : (
                  <Copy size={14} />
                )}
              </button>
            </MessageAction>
          </MessageActions>
        )}
      </div>
    </Message>
  );
};
