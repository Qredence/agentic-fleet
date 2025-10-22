import { Message, MessageContent } from "@/components/ui/message";
import { Reasoning, ReasoningContent, ReasoningTitle } from "@/components/ui/reasoning";
import { Step, Steps } from "@/components/ui/steps";
import { Tool } from "@/components/ui/tool";
import { cn } from "@/lib/utils";
import { Bot, User } from "lucide-react";
import React from "react";

export type AgentType =
  | "user"
  | "analyst"
  | "researcher"
  | "strategist"
  | "coordinator"
  | "worker"
  | "coordinator";

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
  strategist: {
    name: "Strategy Agent",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-accent/50",
  },
  coordinator: {
    name: "Coordinator",
    icon: Bot,
    color: "text-foreground",
    bgColor: "bg-muted/40",
  },
};

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
  }: ChatMessageProps) => {
    const config = agentConfig[agent];
    const Icon = config.icon;

    return (
      <Message
        className={cn(
          "p-4 hover:bg-muted/30 transition-smooth rounded-lg",
          isNew && "animate-fade-in",
          isStreaming && "animate-pulse-subtle"
        )}
      >
        {/* Avatar */}
        <div
          className={cn(
            "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
            config.bgColor
          )}
        >
          <Icon className={cn("h-4 w-4", config.color)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-3">
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-sm font-semibold text-foreground">{config.name}</span>
            <span className="text-xs text-muted-foreground">{timestamp}</span>
          </div>

          {/* Reasoning Block */}
          {reasoning && (
            <Reasoning>
              <ReasoningTitle>{config.name} is thinking...</ReasoningTitle>
              <ReasoningContent>{reasoning}</ReasoningContent>
            </Reasoning>
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
          <MessageContent
            markdown={true}
            className="bg-transparent p-4 border border-border/50 rounded-lg"
          >
            {message}
          </MessageContent>
        </div>
      </Message>
    );
  }
);
