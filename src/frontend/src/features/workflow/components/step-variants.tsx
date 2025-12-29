import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Markdown } from "@/features/chat/components";
import { WorkflowRequestResponder } from "./workflow-request-responder";
import { coerceString, formatExtraDataMarkdown } from "./utils";
import type { ConversationStep } from "@/api/types";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  Circle,
  GitBranch,
  Lightbulb,
  CheckCircle2,
  ActivitySquare,
  MessageSquare,
  Play,
  CheckCircle,
  Eye,
  AlertCircle,
} from "lucide-react";
import React from "react";

// Icon mapping for different step kinds and types
const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  routing: GitBranch,
  analysis: Lightbulb,
  quality: CheckCircle2,
  progress: ActivitySquare,
  request: MessageSquare,
  agent_start: Play,
  agent_complete: CheckCircle,
  agent_output: Eye,
  error: AlertCircle,
};

function getIconForStep(
  step: ConversationStep,
): React.ComponentType<{ className?: string }> | null {
  const iconHint = step.uiHint?.iconHint;
  if (iconHint && ICON_MAP[iconHint]) {
    return ICON_MAP[iconHint];
  }
  if (step.kind && ICON_MAP[step.kind]) {
    return ICON_MAP[step.kind];
  }
  if (step.type && ICON_MAP[step.type]) {
    return ICON_MAP[step.type];
  }
  return null;
}

// Priority-based styling
function getPriorityStyles(priority: string | undefined): {
  borderClass: string;
  badgeClass: string;
  iconClass: string;
} {
  switch (priority) {
    case "high":
      return {
        borderClass: "border-l-4 border-l-blue-500",
        badgeClass: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
        iconClass: "text-blue-600 dark:text-blue-400",
      };
    case "medium":
      return {
        borderClass: "border-l-2 border-l-muted-foreground/30",
        badgeClass: "bg-muted text-muted-foreground",
        iconClass: "text-muted-foreground",
      };
    case "low":
    default:
      return {
        borderClass: "border-l border-l-muted-foreground/20",
        badgeClass: "bg-muted/50 text-muted-foreground/70",
        iconClass: "text-muted-foreground/60",
      };
  }
}

export interface StepVariantProps {
  step: ConversationStep;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  triggerLabel: string;
  isLast?: boolean;
  onWorkflowResponse: (requestId: string, payload: unknown) => void;
  isLoading: boolean;
}

// Reusable content renderer
function StepContent({
  step,
  onWorkflowResponse,
  isLoading,
}: {
  step: ConversationStep;
  onWorkflowResponse: (requestId: string, payload: unknown) => void;
  isLoading: boolean;
}) {
  // Extract reasoning summary fields
  const reasoningSummaryFields = [
    "complexity",
    "capabilities",
    "steps",
    "intent",
    "intent_confidence",
    "reasoning",
    "subtasks",
    "assigned_to",
    "mode",
  ];

  const reasoningSummary: Record<string, unknown> = {};
  let hasReasoningSummary = false;

  if (step.data) {
    for (const field of reasoningSummaryFields) {
      if (field in step.data) {
        reasoningSummary[field] = step.data[field];
        hasReasoningSummary = true;
      }
    }
  }

  // Create extra data excluding reasoning summary fields and standard fields
  const extraData = step.data ? { ...step.data } : undefined;
  if (extraData) {
    const fieldsToRemove = [
      "output",
      "request_id",
      "requestId",
      "request_type",
      "author",
      "agent_id",
      ...reasoningSummaryFields,
    ];
    fieldsToRemove.forEach((field) => {
      delete (extraData as Record<string, unknown>)[field];
    });
  }

  const hasExtraData = !!extraData && Object.keys(extraData).length > 0;
  const output =
    typeof step.data?.output === "string" ? step.data.output : undefined;
  const requestId =
    coerceString(step.data?.request_id) ||
    coerceString((step.data as Record<string, unknown> | undefined)?.requestId);
  const requestType = coerceString(step.data?.request_type);

  return (
    <>
      {step.content.trim() ? (
        <div className="text-foreground">
          <Markdown className="prose prose-sm max-w-none whitespace-pre-wrap wrap-break-word">
            {step.content}
          </Markdown>
        </div>
      ) : null}

      {hasReasoningSummary ? (
        <div className="mt-2 space-y-1">
          <div className="text-xs font-medium text-muted-foreground">
            Reasoning summary
          </div>
          <Markdown className="rounded-md bg-muted/20 p-2 text-xs text-muted-foreground prose prose-sm max-w-none">
            {formatExtraDataMarkdown(reasoningSummary)}
          </Markdown>
        </div>
      ) : null}

      {step.type === "request" && requestId ? (
        <div>
          <WorkflowRequestResponder
            requestId={requestId}
            requestType={requestType}
            isLoading={isLoading}
            onSubmit={onWorkflowResponse}
          />
        </div>
      ) : null}

      {output ? (
        <div className="whitespace-pre-wrap wrap-break-word text-foreground">
          {output}
        </div>
      ) : null}

      {hasExtraData ? (
        <div>
          <Markdown className="mt-2 rounded-md bg-muted/20 p-2 text-xs text-muted-foreground prose prose-sm max-w-none">
            {formatExtraDataMarkdown(extraData as Record<string, unknown>)}
          </Markdown>
        </div>
      ) : null}
    </>
  );
}

/**
 * ChatStepVariant - Collapsible step with priority-based borders and icons
 * Used for orchestrator thoughts, agent lifecycle events, etc.
 */
export function ChatStepVariant({
  step,
  isOpen,
  onOpenChange,
  triggerLabel,
  isLast = false,
  onWorkflowResponse,
  isLoading,
}: StepVariantProps) {
  const priority = step.uiHint?.priority;
  const { borderClass, badgeClass, iconClass } = getPriorityStyles(priority);
  const Icon = getIconForStep(step);

  return (
    <Collapsible
      className="group"
      data-last={isLast}
      open={isOpen}
      onOpenChange={onOpenChange}
    >
      <CollapsibleTrigger
        className={cn(
          "group text-muted-foreground hover:text-foreground flex cursor-pointer items-center justify-start gap-1 text-left text-sm transition-colors",
          step.type === "error" && "text-destructive hover:text-destructive",
        )}
      >
        <div className="flex items-center gap-2">
          {Icon ? (
            <span className="relative inline-flex size-4 items-center justify-center">
              <span
                className={cn(
                  "transition-opacity group-hover:opacity-0",
                  iconClass,
                )}
              >
                <Icon className="size-4" />
              </span>
              <ChevronDown className="absolute size-4 opacity-0 transition-opacity group-hover:opacity-100 group-data-[state=open]:rotate-180" />
            </span>
          ) : (
            <span className="relative inline-flex size-4 items-center justify-center">
              <Circle className="size-2 fill-current" />
            </span>
          )}
          <span>{triggerLabel}</span>
          {priority === "high" && (
            <span
              className={cn(
                "ml-2 rounded px-1.5 py-0.5 text-xs font-medium",
                badgeClass,
              )}
            >
              High Priority
            </span>
          )}
        </div>
        {!Icon && (
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        )}
      </CollapsibleTrigger>

      <CollapsibleContent
        className={cn(
          "text-popover-foreground data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down overflow-hidden",
        )}
      >
        <div
          className={cn(
            "grid grid-cols-[min-content_minmax(0,1fr)] gap-x-4",
            borderClass,
          )}
        >
          <div className="bg-muted-foreground/20 ml-2 h-full w-px group-data-[last=true]:hidden" />
          <div className="ml-2 h-full w-px bg-transparent group-data-[last=false]:hidden" />
          <div className="mt-2 space-y-2">
            <StepContent
              step={step}
              onWorkflowResponse={onWorkflowResponse}
              isLoading={isLoading}
            />
          </div>
        </div>
      </CollapsibleContent>

      <div className="flex justify-start group-data-[last=true]:hidden">
        <div className="bg-muted-foreground/20 ml-2 h-4 w-px" />
      </div>
    </Collapsible>
  );
}

/**
 * MessageBubbleVariant - Always-expanded card layout for responses
 * Used for response deltas and final outputs
 */
export function MessageBubbleVariant({
  step,
  onWorkflowResponse,
  isLoading,
}: StepVariantProps) {
  const priority = step.uiHint?.priority;
  const { borderClass } = getPriorityStyles(priority);

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card/60 p-3 shadow-sm",
        borderClass,
      )}
    >
      <StepContent
        step={step}
        onWorkflowResponse={onWorkflowResponse}
        isLoading={isLoading}
      />
    </div>
  );
}

/**
 * InlineTextVariant - Minimal text-only display for low-priority events
 * Used for status updates, progress messages, etc.
 */
export function InlineTextVariant({
  step,
  onWorkflowResponse,
  isLoading,
}: StepVariantProps) {
  return (
    <div className="text-sm text-muted-foreground">
      <StepContent
        step={step}
        onWorkflowResponse={onWorkflowResponse}
        isLoading={isLoading}
      />
    </div>
  );
}
