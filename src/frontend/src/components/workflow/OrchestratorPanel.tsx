import React from "react";
import {
  Brain,
  GitBranch,
  Search,
  ShieldCheck,
  BarChart2,
  Loader2,
} from "lucide-react";
import {
  Steps,
  StepsTrigger,
  StepsContent,
  StepsItem,
} from "../prompt-kit/steps";
import { cn } from "@/lib/utils";
import type { OrchestratorPanelProps } from "./types";
import type { ConversationStep } from "../../api/types";

const getStepIcon = (step: ConversationStep) => {
  switch (step.kind) {
    case "routing":
      return <GitBranch size={12} />;
    case "analysis":
      return <Search size={12} />;
    case "quality":
      return <ShieldCheck size={12} />;
    case "progress":
      return <BarChart2 size={12} />;
    default:
      return <Brain size={12} />;
  }
};

const getStepLabel = (step: ConversationStep): string => {
  if (step.kind === "routing") {
    const data = step.data as Record<string, unknown> | undefined;
    const mode = data?.mode as string | undefined;
    const agents = data?.assigned_to as string[] | undefined;
    if (mode && agents) {
      return `Routing: ${mode} mode → ${agents.join(", ")}`;
    }
  }

  if (step.kind === "analysis") {
    const data = step.data as Record<string, unknown> | undefined;
    const complexity = data?.complexity as string | undefined;
    if (complexity) {
      return `Analysis: ${complexity} complexity`;
    }
  }

  if (step.kind === "quality") {
    const data = step.data as Record<string, unknown> | undefined;
    const score = data?.score as number | undefined;
    if (score !== undefined) {
      return `Quality: ${score.toFixed(1)}/10`;
    }
  }

  return step.content;
};

const getComplexityBadge = (complexity: string) => {
  const colorMap: Record<string, string> = {
    low: "bg-green-500/20 text-green-400 border-green-500/30",
    medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    high: "bg-red-500/20 text-red-400 border-red-500/30",
  };

  return (
    <span
      className={cn(
        "px-1.5 py-0.5 rounded text-xs font-medium border",
        colorMap[complexity] || "bg-muted text-muted-foreground",
      )}
    >
      {complexity}
    </span>
  );
};

const renderStepDetails = (step: ConversationStep) => {
  const data = step.data as Record<string, unknown> | undefined;
  if (!data) return null;

  if (step.kind === "analysis") {
    const complexity = data.complexity as string | undefined;
    const capabilities = data.capabilities as string[] | undefined;
    const estSteps = data.steps as number | undefined;
    return (
      <div className="mt-1 space-y-1 text-xs text-muted-foreground">
        {complexity != null && (
          <div className="flex items-center gap-2">
            <span>Complexity:</span>
            {getComplexityBadge(complexity)}
          </div>
        )}
        {capabilities && capabilities.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            <span>Capabilities:</span>
            {capabilities.map((cap, i) => (
              <span
                key={i}
                className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs"
              >
                {cap}
              </span>
            ))}
          </div>
        )}
        {estSteps != null && (
          <div>
            <span>Est. steps: {estSteps}</span>
          </div>
        )}
      </div>
    );
  }

  if (step.kind === "routing") {
    const mode = data.mode as string | undefined;
    const assigned_to = data.assigned_to as string[] | undefined;
    const subtasks = data.subtasks as string[] | undefined;
    return (
      <div className="mt-1 space-y-1 text-xs text-muted-foreground">
        {mode != null && (
          <div>
            <span className="text-yellow-400 font-medium">{mode}</span> mode
          </div>
        )}
        {assigned_to && assigned_to.length > 0 && (
          <div>Agents: {assigned_to.join(" → ")}</div>
        )}
        {subtasks && subtasks.length > 0 && (
          <details className="mt-1">
            <summary className="cursor-pointer hover:text-foreground">
              {subtasks.length} subtasks
            </summary>
            <ol className="ml-4 mt-1 list-decimal">
              {subtasks.map((task, i) => (
                <li key={i}>{task}</li>
              ))}
            </ol>
          </details>
        )}
      </div>
    );
  }

  if (step.kind === "quality") {
    const score = data.score as number | undefined;
    const missing = data.missing as string[] | undefined;
    const improvements = data.improvements as string[] | undefined;
    const passed = data.passed as boolean | undefined;
    return (
      <div className="mt-1 space-y-1 text-xs text-muted-foreground">
        {score != null && (
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "px-1.5 py-0.5 rounded font-bold border",
                score >= 8
                  ? "bg-green-500/20 text-green-400 border-green-500/30"
                  : score >= 5
                    ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                    : "bg-red-500/20 text-red-400 border-red-500/30",
              )}
            >
              {score.toFixed(1)}/10
            </span>
            {passed != null && (
              <span className={passed ? "text-green-400" : "text-red-400"}>
                {passed ? "✓ Passed" : "✗ Failed"}
              </span>
            )}
          </div>
        )}
        {missing && missing.length > 0 && (
          <div>
            <span className="text-red-400">Missing:</span> {missing.join(", ")}
          </div>
        )}
        {improvements && improvements.length > 0 && (
          <div>
            <span className="text-blue-400">Suggestions:</span>{" "}
            {improvements.join(", ")}
          </div>
        )}
      </div>
    );
  }

  return null;
};

export const OrchestratorPanel: React.FC<OrchestratorPanelProps> = ({
  steps,
  isActive,
}) => {
  if (steps.length === 0) return null;

  return (
    <div className="bg-muted/20 rounded-lg p-3 mb-4 border border-muted">
      {isActive && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
          <Loader2 size={14} className="animate-spin" />
          <span>Orchestrator processing...</span>
        </div>
      )}

      <Steps defaultOpen={true}>
        <StepsTrigger leftIcon={<Brain size={14} />} className="font-medium">
          Workflow Progress ({steps.length} steps)
        </StepsTrigger>
        <StepsContent>
          {steps.map((step) => (
            <StepsItem key={step.id} className="py-1">
              <div className="flex items-start gap-2">
                <span className="mt-0.5 text-muted-foreground">
                  {getStepIcon(step)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm">{getStepLabel(step)}</div>
                  {renderStepDetails(step)}
                </div>
              </div>
            </StepsItem>
          ))}
        </StepsContent>
      </Steps>
    </div>
  );
};

export default OrchestratorPanel;
