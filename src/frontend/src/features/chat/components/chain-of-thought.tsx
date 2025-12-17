import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "./collapsible";
import { Markdown } from "./markdown";
import { TextShimmer } from "./text-shimmer";
import { WorkflowRequestResponder } from "./workflow-request-responder";
import {
  coerceString,
  formatExtraDataMarkdown,
  formatStepTime,
  getStepLabel,
  splitSteps,
} from "./utils";
import type { Message as ChatMessage } from "@/api/types";
import { cn } from "@/shared/lib/utils";
import { ChevronDown, Circle } from "lucide-react";
import React, { useMemo } from "react";

export type ChainOfThoughtItemProps = React.ComponentProps<"div">;

export const ChainOfThoughtItem = ({
  children,
  className,
  ...props
}: ChainOfThoughtItemProps) => (
  <div className={cn("text-muted-foreground text-sm", className)} {...props}>
    {children}
  </div>
);

export type ChainOfThoughtTriggerProps = React.ComponentProps<
  typeof CollapsibleTrigger
> & {
  leftIcon?: React.ReactNode;
  swapIconOnHover?: boolean;
};

export const ChainOfThoughtTrigger = ({
  children,
  className,
  leftIcon,
  swapIconOnHover = true,
  ...props
}: ChainOfThoughtTriggerProps) => (
  <CollapsibleTrigger
    className={cn(
      "group text-muted-foreground hover:text-foreground flex cursor-pointer items-center justify-start gap-1 text-left text-sm transition-colors",
      className,
    )}
    {...props}
  >
    <div className="flex items-center gap-2">
      {leftIcon ? (
        <span className="relative inline-flex size-4 items-center justify-center">
          <span
            className={cn(
              "transition-opacity",
              swapIconOnHover && "group-hover:opacity-0",
            )}
          >
            {leftIcon}
          </span>
          {swapIconOnHover && (
            <ChevronDown className="absolute size-4 opacity-0 transition-opacity group-hover:opacity-100 group-data-[state=open]:rotate-180" />
          )}
        </span>
      ) : (
        <span className="relative inline-flex size-4 items-center justify-center">
          <Circle className="size-2 fill-current" />
        </span>
      )}
      <span>{children}</span>
    </div>
    {!leftIcon && (
      <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
    )}
  </CollapsibleTrigger>
);

export type ChainOfThoughtContentProps = React.ComponentProps<
  typeof CollapsibleContent
>;

export const ChainOfThoughtContent = ({
  children,
  className,
  ...props
}: ChainOfThoughtContentProps) => {
  return (
    <CollapsibleContent
      className={cn(
        "text-popover-foreground data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down overflow-hidden",
        className,
      )}
      {...props}
    >
      <div className="grid grid-cols-[min-content_minmax(0,1fr)] gap-x-4">
        <div className="bg-muted-foreground/20 ml-2 h-full w-px group-data-[last=true]:hidden" />
        <div className="ml-2 h-full w-px bg-transparent group-data-[last=false]:hidden" />
        <div className="mt-2 space-y-2">{children}</div>
      </div>
    </CollapsibleContent>
  );
};

export type ChainOfThoughtProps = {
  children: React.ReactNode;
  className?: string;
};

export function ChainOfThought({ children, className }: ChainOfThoughtProps) {
  const childrenArray = React.Children.toArray(children);

  return (
    <div className={cn("space-y-0", className)}>
      {childrenArray.map((child, index) => (
        <React.Fragment key={index}>
          {React.isValidElement(child) &&
            React.cloneElement(
              child as React.ReactElement<ChainOfThoughtStepProps>,
              {
                isLast: index === childrenArray.length - 1,
              },
            )}
        </React.Fragment>
      ))}
    </div>
  );
}

export type ChainOfThoughtStepProps = {
  children: React.ReactNode;
  className?: string;
  isLast?: boolean;
};

export const ChainOfThoughtStep = ({
  children,
  className,
  isLast = false,
  ...props
}: ChainOfThoughtStepProps & React.ComponentProps<typeof Collapsible>) => {
  return (
    <Collapsible
      className={cn("group", className)}
      data-last={isLast}
      {...props}
    >
      {children}
      <div className="flex justify-start group-data-[last=true]:hidden">
        <div className="bg-muted-foreground/20 ml-2 h-4 w-px" />
      </div>
    </Collapsible>
  );
};

export type ChainOfThoughtTraceProps = {
  message: ChatMessage;
  isStreaming?: boolean;
  onWorkflowResponse: (requestId: string, payload: unknown) => void;
  isLoading: boolean;
};

function extractCapability(
  data: Record<string, unknown> | undefined,
): string | undefined {
  if (!data) return undefined;
  const capabilities = data.capabilities;
  if (typeof capabilities === "string") return capabilities;
  if (Array.isArray(capabilities) && capabilities.length > 0) {
    return typeof capabilities[0] === "string" ? capabilities[0] : undefined;
  }
  return undefined;
}

function extractReasoningSummary(
  data: Record<string, unknown> | undefined,
): Record<string, unknown> | undefined {
  if (!data) return undefined;
  const summaryFields = [
    "complexity",
    "capabilities",
    "steps",
    "intent",
    "intent_confidence",
    "reasoning",
  ];
  const summary: Record<string, unknown> = {};
  let hasSummary = false;

  for (const field of summaryFields) {
    if (field in data) {
      summary[field] = data[field];
      hasSummary = true;
    }
  }

  return hasSummary ? summary : undefined;
}

function formatTriggerLabel(
  label: string,
  capability: string | undefined,
  time: string,
): string {
  const capitalizedLabel =
    label.charAt(0).toUpperCase() + label.slice(1).toLowerCase();
  const parts = ["Event", capitalizedLabel];
  if (capability) {
    parts.push(`using ${capability}`);
  }
  if (time) {
    parts.push(time);
  }
  return parts.join(" · ");
}

export function ChainOfThoughtTrace({
  message,
  isStreaming = false,
  onWorkflowResponse,
  isLoading,
}: ChainOfThoughtTraceProps) {
  const steps = useMemo(() => message.steps ?? [], [message.steps]);
  const phase = (message.workflowPhase || "").trim();

  if (steps.length === 0 && !phase) return null;

  const { reasoning, trace } = splitSteps(steps);

  return (
    <div className="w-full space-y-3">
      {phase && isStreaming && !message.content ? (
        <div className="text-sm text-muted-foreground">
          <TextShimmer as="span">{phase}</TextShimmer>
        </div>
      ) : null}

      {reasoning.trim() ? (
        <Collapsible className="w-full">
          <CollapsibleTrigger className="text-muted-foreground hover:text-foreground flex cursor-pointer items-center justify-start gap-1 text-left text-xs transition-colors">
            <span>Reasoning</span>
            <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 overflow-hidden">
            <div className="whitespace-pre-wrap wrap-break-word text-sm text-foreground data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
              {reasoning}
            </div>
          </CollapsibleContent>
        </Collapsible>
      ) : null}

      {trace.length ? (
        <div className="rounded-lg border border-border bg-card/40 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            {isStreaming ? (
              <TextShimmer as="span" className="text-sm">
                Events
              </TextShimmer>
            ) : (
              <span className="text-sm text-muted-foreground">Events</span>
            )}
            <span className="text-xs text-muted-foreground">
              {trace.length}
            </span>
          </div>

          <ChainOfThought className="mt-2">
            {trace.map((step) => {
              const { label } = getStepLabel(step);
              const time = formatStepTime(step.timestamp);
              const capability = extractCapability(step.data);
              const output =
                typeof step.data?.output === "string"
                  ? step.data.output
                  : undefined;
              const requestId =
                coerceString(step.data?.request_id) ||
                coerceString(
                  (step.data as Record<string, unknown> | undefined)?.requestId,
                );
              const requestType = coerceString(step.data?.request_type);

              // Extract reasoning summary fields
              const reasoningSummary = extractReasoningSummary(step.data);

              // Create extra data excluding reasoning summary fields and output
              const extraData = step.data ? { ...step.data } : undefined;
              if (extraData) {
                delete (extraData as Record<string, unknown>).output;
                delete (extraData as Record<string, unknown>).request_id;
                delete (extraData as Record<string, unknown>).requestId;
                delete (extraData as Record<string, unknown>).request_type;
                delete (extraData as Record<string, unknown>).author;
                delete (extraData as Record<string, unknown>).agent_id;
                // Remove reasoning summary fields
                if (reasoningSummary) {
                  Object.keys(reasoningSummary).forEach((key) => {
                    delete (extraData as Record<string, unknown>)[key];
                  });
                }
              }
              const hasExtraData =
                !!extraData && Object.keys(extraData).length > 0;

              // Format trigger label
              const triggerLabel = formatTriggerLabel(label, capability, time);

              return (
                <ChainOfThoughtStep key={step.id} defaultOpen={false}>
                  <ChainOfThoughtTrigger
                    className={cn(
                      step.type === "error" &&
                        "text-destructive hover:text-destructive",
                    )}
                  >
                    {triggerLabel}
                  </ChainOfThoughtTrigger>

                  <ChainOfThoughtContent>
                    {step.content.trim() ? (
                      <ChainOfThoughtItem className="text-foreground">
                        <Markdown className="prose prose-sm max-w-none whitespace-pre-wrap wrap-break-word">
                          {step.content}
                        </Markdown>
                      </ChainOfThoughtItem>
                    ) : null}

                    {reasoningSummary ? (
                      <ChainOfThoughtItem>
                        <div className="mt-2 space-y-1">
                          <div className="text-xs font-medium text-muted-foreground">
                            Reasoning summary
                          </div>
                          <Markdown className="rounded-md bg-muted/20 p-2 text-xs text-muted-foreground prose prose-sm max-w-none">
                            {formatExtraDataMarkdown(reasoningSummary)}
                          </Markdown>
                        </div>
                      </ChainOfThoughtItem>
                    ) : null}

                    {step.type === "request" && requestId ? (
                      <ChainOfThoughtItem>
                        <WorkflowRequestResponder
                          requestId={requestId}
                          requestType={requestType}
                          isLoading={isLoading}
                          onSubmit={onWorkflowResponse}
                        />
                      </ChainOfThoughtItem>
                    ) : null}

                    {output ? (
                      <ChainOfThoughtItem className="whitespace-pre-wrap wrap-break-word text-foreground">
                        {output}
                      </ChainOfThoughtItem>
                    ) : null}

                    {hasExtraData ? (
                      <ChainOfThoughtItem>
                        <Markdown className="mt-2 rounded-md bg-muted/20 p-2 text-xs text-muted-foreground prose prose-sm max-w-none">
                          {formatExtraDataMarkdown(
                            extraData as Record<string, unknown>,
                          )}
                        </Markdown>
                      </ChainOfThoughtItem>
                    ) : null}
                  </ChainOfThoughtContent>
                </ChainOfThoughtStep>
              );
            })}
          </ChainOfThought>
        </div>
      ) : null}
    </div>
  );
}
