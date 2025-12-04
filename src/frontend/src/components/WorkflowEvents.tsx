"use client";

import React from "react";
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

interface WorkflowEventsProps {
  steps: ConversationStep[];
  isStreaming?: boolean;
  workflowPhase?: string;
  className?: string;
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
  // Clean up agent prefixes if present (e.g., "AgentName: message" -> "message" when redundant)
  // Keep the original content for now, but could be refined
  return content;
}

export const WorkflowEvents: React.FC<WorkflowEventsProps> = ({
  steps,
  isStreaming = false,
  workflowPhase,
  className,
}) => {
  const workflowSteps = steps.filter(isWorkflowEvent);

  if (workflowSteps.length === 0 && !isStreaming) {
    return null;
  }

  const eventCount = workflowSteps.length;

  return (
    <div className={cn("mb-3", className)}>
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
            {workflowSteps.map((step, index) => {
              const isLatest = index === workflowSteps.length - 1;
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
    </div>
  );
};

export default WorkflowEvents;
