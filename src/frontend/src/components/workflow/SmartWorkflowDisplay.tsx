"use client";

import React from "react";
import type { ConversationStep } from "../../api/types";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "../prompt-kit/reasoning";
import {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
} from "../prompt-kit/chain-of-thought";
import { cn } from "@/lib/utils";
import { Brain, GitBranch, Search, ShieldCheck, Sparkles } from "lucide-react";

interface SmartWorkflowDisplayProps {
  steps: ConversationStep[];
  reasoning?: string;
  isReasoningStreaming?: boolean;
  className?: string;
}

type StepData = Record<string, unknown>;

const getStepIcon = (kind: string | undefined) => {
  switch (kind) {
    case "analysis":
      return <Search size={14} className="text-cyan-400" />;
    case "routing":
      return <GitBranch size={14} className="text-yellow-400" />;
    case "quality":
      return <ShieldCheck size={14} className="text-green-400" />;
    default:
      return <Sparkles size={14} className="text-purple-400" />;
  }
};

const getComplexityColor = (complexity: string | undefined) => {
  switch (complexity) {
    case "low":
      return "text-green-400";
    case "medium":
      return "text-yellow-400";
    case "high":
      return "text-red-400";
    default:
      return "text-muted-foreground";
  }
};

/**
 * Smart workflow display that chooses the right component based on content:
 * - Reasoning component for GPT reasoning tokens
 * - ChainOfThought for analysis/routing decisions
 * - Nothing for generic status messages
 */
export const SmartWorkflowDisplay: React.FC<SmartWorkflowDisplayProps> = ({
  steps,
  reasoning,
  isReasoningStreaming,
  className,
}) => {
  // Priority 1: Show reasoning if available (GPT-5 reasoning tokens)
  if (reasoning) {
    return (
      <div className={cn("space-y-2", className)}>
        <Reasoning isStreaming={isReasoningStreaming}>
          <ReasoningTrigger className="text-sm text-muted-foreground hover:text-foreground">
            <Brain size={14} className="mr-1 inline" />
            Reasoning
          </ReasoningTrigger>
          <ReasoningContent markdown className="mt-2 pl-5">
            {reasoning}
          </ReasoningContent>
        </Reasoning>
      </div>
    );
  }

  // Priority 2: Filter for meaningful thought steps (analysis, routing, quality)
  const thoughtSteps = steps.filter(
    (s) =>
      s.kind === "analysis" ||
      s.kind === "routing" ||
      s.kind === "quality" ||
      (s.type === "thought" && s.content.length > 30),
  );

  // If no meaningful steps, return nothing
  if (thoughtSteps.length === 0) {
    return null;
  }

  // Show chain of thought for decision process
  return (
    <div className={cn("space-y-1", className)}>
      <ChainOfThought>
        {thoughtSteps.map((step, index) => {
          const data = step.data as StepData | undefined;
          const stepReasoning = data?.reasoning as string | undefined;
          const hasExpandableContent = Boolean(stepReasoning);

          return (
            <ChainOfThoughtStep
              key={step.id || index}
              defaultOpen={index === thoughtSteps.length - 1}
            >
              <ChainOfThoughtTrigger
                leftIcon={getStepIcon(step.kind)}
                swapIconOnHover={hasExpandableContent}
              >
                <span className="text-sm">{step.content}</span>
              </ChainOfThoughtTrigger>

              {hasExpandableContent && (
                <ChainOfThoughtContent>
                  {/* Reasoning explanation */}
                  {stepReasoning && (
                    <ChainOfThoughtItem className="text-muted-foreground/80 italic">
                      {stepReasoning}
                    </ChainOfThoughtItem>
                  )}

                  {/* Analysis details */}
                  {step.kind === "analysis" && data && (
                    <div className="space-y-1 text-xs">
                      {data.complexity != null && (
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">
                            Complexity:
                          </span>
                          <span
                            className={cn(
                              "font-medium",
                              getComplexityColor(String(data.complexity)),
                            )}
                          >
                            {String(data.complexity)}
                          </span>
                        </div>
                      )}
                      {data.intent != null && (
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Intent:</span>
                          <span className="text-blue-400">
                            {String(data.intent)}
                          </span>
                          {data.intent_confidence != null && (
                            <span className="text-muted-foreground/60">
                              (
                              {(Number(data.intent_confidence) * 100).toFixed(
                                0,
                              )}
                              %)
                            </span>
                          )}
                        </div>
                      )}
                      {Array.isArray(data.capabilities) &&
                        data.capabilities.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            <span className="text-muted-foreground">
                              Capabilities:
                            </span>
                            {(data.capabilities as string[]).map((cap, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs"
                              >
                                {cap}
                              </span>
                            ))}
                          </div>
                        )}
                    </div>
                  )}

                  {/* Routing details */}
                  {step.kind === "routing" && data && (
                    <div className="space-y-1 text-xs">
                      {Array.isArray(data.assigned_to) &&
                        data.assigned_to.length > 0 && (
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">
                              Agents:
                            </span>
                            <span className="text-yellow-400">
                              {(data.assigned_to as string[]).join(" → ")}
                            </span>
                          </div>
                        )}
                      {Array.isArray(data.subtasks) &&
                        data.subtasks.length > 0 && (
                          <div className="mt-1">
                            <span className="text-muted-foreground">
                              Subtasks:
                            </span>
                            <ol className="ml-4 mt-1 list-decimal text-muted-foreground/80">
                              {(data.subtasks as string[]).map((task, i) => (
                                <li key={i}>{task}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                    </div>
                  )}

                  {/* Quality details */}
                  {step.kind === "quality" && data && (
                    <div className="space-y-1 text-xs">
                      {data.score != null && (
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Score:</span>
                          <span
                            className={cn(
                              "font-bold",
                              (data.score as number) >= 8
                                ? "text-green-400"
                                : (data.score as number) >= 5
                                  ? "text-yellow-400"
                                  : "text-red-400",
                            )}
                          >
                            {(data.score as number).toFixed(1)}/10
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </ChainOfThoughtContent>
              )}
            </ChainOfThoughtStep>
          );
        })}
      </ChainOfThought>
    </div>
  );
};

export default SmartWorkflowDisplay;
