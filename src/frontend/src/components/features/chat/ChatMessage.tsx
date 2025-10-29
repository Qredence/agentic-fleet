import { ResponseStream } from "@/components/ai/response-stream";
import { Step, Steps } from "@/components/ai/steps";
import { Tool } from "@/components/ai/tool";
import { Message, MessageContent } from "@/components/ui/custom/message";
// Import new prompt-kit components for enhanced features
import {
  Reasoning as PromptReasoning,
  ReasoningContent as PromptReasoningContent,
  ReasoningTrigger,
} from "@/components/ui/prompt-kit";
import type { WorkflowEventType } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AlertCircle, Bot, CheckCircle, Cog, User, Wrench } from "lucide-react";
import React from "react";

export type AgentType =
  | "user"
  | "analyst"
  | "researcher"
  | "coder"
  | "verifier"
  | "manager"
  | "generator"
  | "executor"
  | "planner"
  | "router"
  | "calculator"
  | "responder";

type AgentConfigEntry = {
  name: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  color: string;
  bgColor: string;
};

export interface ToolUsage {
  name: string;
  status: "running" | "complete" | "error";
  description: string;
  icon?: React.ReactNode;
}

export interface StepItem {
  label: string;
  status: "pending" | "current" | "complete" | "error";
}

interface ChatMessageProps {
  message: string;
  agent: AgentType;
  timestamp: string;
  isNew?: boolean;
  isStreaming?: boolean;
  reasoning?: string;
  tools?: ToolUsage[];
  steps?: StepItem[];
  eventType?: WorkflowEventType;
  eventMetadata?: Record<string, unknown>;
  agentRole?: string; // Backend role (router, calculator, manager, etc.)
  confidence?: number; // Confidence level (0-1)
  complexity?: string; // Query complexity level
}

// Helper to get workflow event icon
function getWorkflowEventIcon(eventType: WorkflowEventType) {
  switch (eventType) {
    case "spawn":
      return <Bot className="h-4 w-4" />;
    case "progress":
      return <Cog className="h-4 w-4" />;
    case "tool_call":
      return <Wrench className="h-4 w-4" />;
    case "completion":
      return <CheckCircle className="h-4 w-4" />;
    case "error":
      return <AlertCircle className="h-4 w-4 text-destructive" />;
    default:
      return <Cog className="h-4 w-4" />;
  }
}

const agentConfig = {
  user: {
    name: "You",
    icon: User,
    color: "text-foreground",
    bgColor: "bg-accent/50",
  },
  analyst: {
    name: "Data Analyst",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-secondary/50",
  },
  researcher: {
    name: "Research Agent",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/30",
  },
  coder: {
    name: "Coding Agent",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/30",
  },
  verifier: {
    name: "Verification Agent",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-accent/50",
  },
  manager: {
    name: "Manager",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/40",
  },
  generator: {
    name: "Generator",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/40",
  },
  executor: {
    name: "Executor",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/40",
  },
  planner: {
    name: "Planner",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/40",
  },
  router: {
    name: "Query Router",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-purple-100 dark:bg-purple-900/20",
  },
  calculator: {
    name: "Direct Computer",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-green-100 dark:bg-green-900/20",
  },
  responder: {
    name: "Direct Response",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-blue-100 dark:bg-blue-900/20",
  },
} satisfies Record<AgentType, AgentConfigEntry>;

export const ChatMessage = React.memo(
  ({
    message,
    agent,
    timestamp,
    isNew,
    isStreaming,
    reasoning,
    tools,
    steps,
    eventType,
    eventMetadata: _eventMetadata,
    agentRole,
    confidence,
    complexity,
  }: ChatMessageProps) => {
    const config = agentConfig[agent];
    const Icon = config.icon;

    const isUserMessage = agent === "user";
    const isWorkflowEvent = eventType !== undefined;

    const messageBgClass = isUserMessage
      ? "bg-[hsl(var(--message-user-bg))]"
      : isWorkflowEvent
        ? "bg-muted/30 border-border/30"
        : "bg-[hsl(var(--message-agent-bg))]";

    // Get complexity badge color
    const getComplexityColor = (comp?: string) => {
      switch (comp) {
        case "trivial":
          return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
        case "simple":
          return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
        case "moderate":
          return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
        case "complex":
          return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
        default:
          return "bg-muted text-muted-foreground";
      }
    };

    // Render workflow events with distinctive styling
    if (isWorkflowEvent) {
      const eventIcon = getWorkflowEventIcon(eventType);
      return (
        <Message
          className={cn(
            "p-3 transition-smooth rounded-lg justify-center opacity-90",
            isNew && "animate-fade-in"
          )}
        >
          <div className="flex items-start gap-3 w-full max-w-[700px]">
            <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center bg-muted">
              {eventIcon}
            </div>
            <div className="flex-1 min-w-0 space-y-1">
              {/* Actor and Role Header */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-sm">{config.name}</span>
                {agentRole && <span className="text-xs text-muted-foreground">({agentRole})</span>}
                {confidence !== undefined && (
                  <span className="text-xs text-muted-foreground">
                    • {Math.round(confidence * 100)}% confident
                  </span>
                )}
                {complexity && (
                  <span
                    className={cn(
                      "text-xs px-2 py-0.5 rounded-full font-medium",
                      getComplexityColor(complexity)
                    )}
                  >
                    {complexity}
                  </span>
                )}
              </div>

              {/* Event Message */}
              <div className={cn("text-sm p-2 rounded border", messageBgClass)}>{message}</div>

              {/* Reasoning (if available) */}
              {reasoning && (
                <div className="text-xs text-muted-foreground italic pl-4 border-l-2 border-muted-foreground/30">
                  💭 {reasoning}
                </div>
              )}

              {/* Timestamp */}
              <span className="text-xs text-muted-foreground block">{timestamp}</span>
            </div>
          </div>
        </Message>
      );
    }

    return (
      <Message
        className={cn(
          "p-3 sm:p-4 transition-smooth rounded-lg justify-center",
          isNew && "animate-fade-in",
          isStreaming && "animate-pulse-subtle",
          isUserMessage ? "flex-row-reverse pl-8 sm:pl-10" : "flex-row pr-8 sm:pr-10"
        )}
      >
        {/* Avatar */}
        <div
          className={cn(
            "flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center",
            config.bgColor
          )}
        >
          <Icon className={cn("h-3.5 w-3.5 sm:h-4 sm:w-4", config.color)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 max-w-[700px]">
          <div className="w-full">
            <div
              className={cn(
                "flex items-center gap-1.5 sm:gap-2 mb-1",
                isUserMessage ? "justify-end" : "justify-start"
              )}
            >
              {!isUserMessage && (
                <span className="text-xs sm:text-sm font-semibold text-foreground">{config.name}</span>
              )}
              <span className="text-xs text-muted-foreground">{timestamp}</span>
              {isUserMessage && (
                <span className="text-xs sm:text-sm font-semibold text-foreground">{config.name}</span>
              )}
            </div>

            {/* Enhanced Reasoning Block */}
            {reasoning && (
              <PromptReasoning isStreaming={isStreaming}>
                <ReasoningTrigger className="text-xs text-muted-foreground mb-2">
                  💭 {config.name} is thinking...
                </ReasoningTrigger>
                <PromptReasoningContent markdown={true} className="text-xs sm:text-sm">
                  {reasoning}
                </PromptReasoningContent>
              </PromptReasoning>
            )}

            {/* Steps */}
            {steps && steps.length > 0 && (
              <Steps>
                {steps.map((step, i) => (
                  <Step key={i} status={step.status}>
                    {step.label}
                  </Step>
                ))}
              </Steps>
            )}

            {/* Tools */}
            {tools && tools.length > 0 && (
              <div className="space-y-2">
                {tools.map((tool, i) => (
                  <Tool key={i} name={tool.name} status={tool.status} icon={tool.icon}>
                    {tool.description}
                  </Tool>
                ))}
              </div>
            )}

            {/* Main Message */}
            {isNew || isStreaming ? (
              <div
                className={`p-4 sm:p-6 border border-border/50 w-full rounded-2xl sm:rounded-[32px] ${messageBgClass} flex flex-col justify-center items-start prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none`}
              >
                <ResponseStream
                  textStream={message}
                  mode="typewriter"
                  speed={40}
                  className="w-full"
                  onComplete={() => {
                    // Optional: Handle stream completion
                  }}
                />
              </div>
            ) : (
              <MessageContent
                markdown={true}
                className={`p-4 sm:p-6 border border-border/50 w-full rounded-2xl sm:rounded-[32px] ${messageBgClass} flex flex-col justify-center items-start`}
              >
                {message}
              </MessageContent>
            )}
          </div>
        </div>
      </Message>
    );
  }
);
