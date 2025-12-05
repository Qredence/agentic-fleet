"use client";

import React, { useState } from "react";
import {
  Wrench,
  Bot,
  CheckCircle2,
  Play,
  GitBranch,
  Search,
  ShieldCheck,
  CircleDashed,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { ConversationStep } from "../api/types";
import {
  Steps,
  StepsTrigger,
  StepsContent,
  StepsItem,
} from "./prompt-kit/steps";
import { TextShimmer } from "./prompt-kit/text-shimmer";
import { cn } from "@/lib/utils";
import { WORKFLOW_EVENT_TYPES, type WorkflowEventType } from "../lib/constants";
import {
  WorkflowRenderer,
  SmartWorkflowDisplay,
  filterUsefulSteps,
  getFilteredSummary,
} from "./workflow";

interface WorkflowEventsProps {
  steps: ConversationStep[];
  isStreaming?: boolean;
  workflowPhase?: string;
  className?: string;
  /** Current reasoning content (for GPT-5 reasoning tokens) */
  reasoning?: string;
  /** Whether reasoning is currently streaming */
  isReasoningStreaming?: boolean;
  /** Use grouped rendering by agent (new UX) */
  useGroupedView?: boolean;
}

function isWorkflowEvent(step: ConversationStep): boolean {
  return WORKFLOW_EVENT_TYPES.includes(step.type as WorkflowEventType);
}

function getEventIcon(step: ConversationStep): React.ReactNode {
  // Check for specific patterns in content for tool-related events
  const content = step.content.toLowerCase();

  if (
    content.includes("tool") ||
    content.includes("mcp") ||
    content.includes("initialized")
  ) {
    return <Wrench size={14} className="text-blue-400" />;
  }

  if (
    content.includes("created") &&
    (content.includes("agent") || content.includes("dspy"))
  ) {
    return <Bot size={14} className="text-purple-400" />;
  }

  // Icon based on step kind
  switch (step.kind) {
    case "routing":
      return <GitBranch size={14} className="text-yellow-400" />;
    case "analysis":
      return <Search size={14} className="text-cyan-400" />;
    case "quality":
      return <ShieldCheck size={14} className="text-green-400" />;
    case "progress":
      return <CircleDashed size={14} className="text-orange-400" />;
  }

  // Icon based on step type
  switch (step.type) {
    case "agent_start":
      return <Play size={14} className="text-yellow-400" />;
    case "agent_complete":
      return <CheckCircle2 size={14} className="text-green-400" />;
    case "thought":
      return <Search size={14} className="text-blue-300" />;
    case "error":
      return <AlertCircle size={14} className="text-red-400" />;
    default:
      return <CircleDashed size={14} className="text-muted-foreground" />;
  }
}

function formatEventContent(content: string): string {
  return content;
}

// Legacy flat view component
const FlatWorkflowView: React.FC<{
  steps: ConversationStep[];
  isStreaming: boolean;
  workflowPhase?: string;
}> = ({ steps, isStreaming, workflowPhase }) => {
  const eventCount = steps.length;

  return (
    <Steps defaultOpen={true} className="bg-muted/10 rounded-lg p-2">
      <StepsTrigger
        leftIcon={
          isStreaming ? (
            <Loader2 size={14} className="animate-spin text-blue-400" />
          ) : (
            <CheckCircle2 size={14} className="text-green-400" />
          )
        }
        className="text-xs uppercase tracking-wide text-muted-foreground"
      >
        <span className="flex items-center gap-2">
          {isStreaming ? (
            <>
              <TextShimmer
                duration={2}
                spread={30}
                className="inline-block min-w-[120px]"
              >
                {workflowPhase || "Processing..."}
              </TextShimmer>
              <span className="text-muted-foreground/60">
                ({eventCount} {eventCount === 1 ? "event" : "events"})
              </span>
            </>
          ) : (
            <span>
              {eventCount} workflow {eventCount === 1 ? "event" : "events"}
            </span>
          )}
        </span>
      </StepsTrigger>
      <StepsContent>
        <div className="space-y-1">
          {steps.map((step, index) => {
            const isLatest = index === steps.length - 1;
            const showShimmer = isStreaming && isLatest;

            return (
              <StepsItem
                key={step.id || index}
                className={cn(
                  "flex items-start gap-2",
                  isLatest && isStreaming && "text-foreground",
                )}
              >
                <span className="mt-0.5 shrink-0">{getEventIcon(step)}</span>
                <span className="flex-1">
                  {showShimmer ? (
                    <TextShimmer duration={2.5} spread={25}>
                      {formatEventContent(step.content)}
                    </TextShimmer>
                  ) : (
                    formatEventContent(step.content)
                  )}
                </span>
                <span className="text-[10px] text-muted-foreground/50 shrink-0 ml-auto">
                  {new Date(step.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
              </StepsItem>
            );
          })}
        </div>
      </StepsContent>
    </Steps>
  );
};

export const WorkflowEvents: React.FC<WorkflowEventsProps> = ({
  steps,
  isStreaming = false,
  workflowPhase,
  className,
  reasoning,
  isReasoningStreaming,
  useGroupedView = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const workflowSteps = steps.filter(isWorkflowEvent);

  // Filter out generic status messages that don't add value
  const usefulSteps = filterUsefulSteps(workflowSteps);

  // Check if we have meaningful content to display
  const hasReasoning = Boolean(reasoning);
  const hasThoughtSteps = usefulSteps.some(
    (s) =>
      s.kind === "analysis" || s.kind === "routing" || s.kind === "quality",
  );

  // Don't show anything if no useful content
  if (
    !hasReasoning &&
    !hasThoughtSteps &&
    usefulSteps.length === 0 &&
    !isStreaming
  ) {
    return null;
  }

  // Use smart display for reasoning and thought chains
  if (useGroupedView && (hasReasoning || hasThoughtSteps)) {
    return (
      <div className={cn("mb-3", className)}>
        <SmartWorkflowDisplay
          steps={usefulSteps}
          reasoning={reasoning}
          isReasoningStreaming={isReasoningStreaming}
        />
      </div>
    );
  }

  // Fallback: Legacy grouped view with collapsible header
  if (useGroupedView && usefulSteps.length > 0) {
    const filteredSummary = getFilteredSummary(workflowSteps, usefulSteps);
    return (
      <div className={cn("mb-3", className)}>
        {/* Collapsible header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground hover:text-foreground transition-colors mb-2 w-full"
        >
          {isStreaming ? (
            <Loader2 size={14} className="animate-spin text-blue-400" />
          ) : (
            <CheckCircle2 size={14} className="text-green-400" />
          )}
          <span className="flex items-center gap-2 flex-1">
            {isStreaming ? (
              <TextShimmer
                duration={2}
                spread={30}
                className="inline-block min-w-[100px]"
              >
                {workflowPhase || "Processing..."}
              </TextShimmer>
            ) : (
              <span>Workflow complete</span>
            )}
            {usefulSteps.length > 0 && (
              <span className="text-muted-foreground/60">
                ({usefulSteps.length}{" "}
                {usefulSteps.length === 1 ? "step" : "steps"})
              </span>
            )}
            {filteredSummary && (
              <span className="text-muted-foreground/40 text-[10px]">
                • {filteredSummary}
              </span>
            )}
          </span>
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {/* Grouped workflow content */}
        {isExpanded && usefulSteps.length > 0 && (
          <div className="bg-muted/10 rounded-lg p-3">
            <WorkflowRenderer
              steps={usefulSteps}
              workflowPhase={workflowPhase}
            />
          </div>
        )}

        {/* Show message when only generic events exist */}
        {isExpanded && usefulSteps.length === 0 && isStreaming && (
          <div className="bg-muted/10 rounded-lg p-3 text-xs text-muted-foreground italic">
            Processing your request...
          </div>
        )}
      </div>
    );
  }

  // Legacy flat view - also filter steps
  return (
    <div className={cn("mb-3", className)}>
      <FlatWorkflowView
        steps={usefulSteps}
        isStreaming={isStreaming}
        workflowPhase={workflowPhase}
      />
    </div>
  );
};

export default WorkflowEvents;
