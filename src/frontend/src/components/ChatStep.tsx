import React from "react";
import {
  Brain,
  CheckCircle2,
  CircleDashed,
  AlertCircle,
  GitBranch,
  Search,
  ShieldCheck,
  Play,
  CheckSquare,
  MessageSquare,
  ArrowRight,
  Wrench,
  BarChart2,
} from "lucide-react";
import type { ConversationStep } from "../api/types";
import {
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
} from "./prompt-kit/chain-of-thought";
import { CodeBlock, CodeBlockCode } from "./prompt-kit/code-block";
import { Markdown } from "./prompt-kit/markdown";
import { cn } from "@/lib/utils";

interface ChatStepProps {
  step: ConversationStep;
  isLast?: boolean;
}

export const ChatStep: React.FC<ChatStepProps> = ({ step, isLast }) => {
  const getIcon = () => {
    switch (step.kind) {
      case "routing":
        return <GitBranch size={14} />;
      case "analysis":
        return <Search size={14} />;
      case "quality":
        return <ShieldCheck size={14} />;
      case "progress":
        return <BarChart2 size={14} />;
      case "handoff":
        return <ArrowRight size={14} />;
      case "tool_call":
        return <Wrench size={14} />;
      default:
        if (step.type === "error") return <AlertCircle size={14} />;
        if (step.type === "thought" || step.type === "agent_thought")
          return <Brain size={14} />;
        if (step.type === "agent_start") return <Play size={14} />;
        if (step.type === "agent_complete") return <CheckSquare size={14} />;
        if (step.type === "agent_output") return <MessageSquare size={14} />;
        if (step.type === "progress") return <CircleDashed size={14} />;
        return <CheckCircle2 size={14} />;
    }
  };

  const getToneClass = () => {
    switch (step.type) {
      case "agent_start":
        return "text-yellow-400";
      case "agent_complete":
        return "text-green-400";
      case "agent_output":
        return "text-purple-400";
      case "agent_thought":
        return "text-blue-300";
      case "error":
        return "text-red-400";
      default:
        return "";
    }
  };

  // Filter out redundant keys from data for display
  const getDisplayData = (): Record<string, unknown> | null => {
    if (!step.data) return null;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { agent_id, author, ...rest } = step.data as Record<string, unknown>;
    // Only show data if there's meaningful content beyond agent_id/author
    if (Object.keys(rest).length === 0) return null;
    return rest;
  };

  const displayData = getDisplayData();
  const hasDetails = displayData && Object.keys(displayData).length > 0;
  const outputContent = displayData?.output;

  // Get quality score color class
  const getQualityScoreClass = (score: number): string => {
    if (score >= 8) return "bg-green-500/20 text-green-400 border-green-500/30";
    if (score >= 5)
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    return "bg-red-500/20 text-red-400 border-red-500/30";
  };

  // Render rich content based on event kind
  const renderRichContent = () => {
    if (!step.data) return null;

    // Routing event rendering
    if (step.kind === "routing") {
      const { mode, assigned_to, subtasks } = step.data as Record<
        string,
        unknown
      >;
      return (
        <div className="space-y-2 text-sm">
          {mode && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Mode:</span>
              <span className="font-medium text-yellow-400">
                {String(mode)}
              </span>
            </div>
          )}
          {assigned_to && Array.isArray(assigned_to) && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Agents:</span>
              <span className="font-medium">
                {(assigned_to as string[]).join(" → ")}
              </span>
            </div>
          )}
          {subtasks && Array.isArray(subtasks) && (
            <details className="mt-2">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                Subtasks ({(subtasks as string[]).length})
              </summary>
              <ol className="mt-2 ml-4 list-decimal space-y-1 text-muted-foreground">
                {(subtasks as string[]).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </details>
          )}
        </div>
      );
    }

    // Analysis event rendering
    if (step.kind === "analysis") {
      const { complexity, capabilities, estimated_steps, task_type } =
        step.data as Record<string, unknown>;
      return (
        <div className="space-y-2 text-sm">
          {complexity && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Complexity:</span>
              <span
                className={cn(
                  "px-2 py-0.5 rounded-full text-xs font-medium border",
                  complexity === "high"
                    ? "bg-red-500/20 text-red-400 border-red-500/30"
                    : complexity === "medium"
                      ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                      : "bg-green-500/20 text-green-400 border-green-500/30",
                )}
              >
                {String(complexity)}
              </span>
            </div>
          )}
          {task_type && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Type:</span>
              <span className="font-medium">{String(task_type)}</span>
            </div>
          )}
          {capabilities && Array.isArray(capabilities) && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-muted-foreground">Capabilities:</span>
              {(capabilities as string[]).map((cap, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs"
                >
                  {cap}
                </span>
              ))}
            </div>
          )}
          {estimated_steps && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Est. Steps:</span>
              <span className="font-medium">{String(estimated_steps)}</span>
            </div>
          )}
        </div>
      );
    }

    // Quality event rendering
    if (step.kind === "quality") {
      const { score, missing_elements, feedback, passed } = step.data as Record<
        string,
        unknown
      >;
      const numScore =
        typeof score === "number" ? score : parseFloat(String(score));
      return (
        <div className="space-y-2 text-sm">
          {!isNaN(numScore) && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Score:</span>
              <span
                className={cn(
                  "px-2 py-0.5 rounded-full text-xs font-bold border",
                  getQualityScoreClass(numScore),
                )}
              >
                {numScore.toFixed(1)}/10
              </span>
              {passed !== undefined && (
                <span
                  className={cn(
                    "text-xs",
                    passed ? "text-green-400" : "text-red-400",
                  )}
                >
                  {passed ? "✓ Passed" : "✗ Failed"}
                </span>
              )}
            </div>
          )}
          {feedback && (
            <div>
              <span className="text-muted-foreground">Feedback:</span>
              <p className="mt-1 text-foreground">{String(feedback)}</p>
            </div>
          )}
          {missing_elements && Array.isArray(missing_elements) && (
            <div>
              <span className="text-muted-foreground">Missing elements:</span>
              <ul className="mt-1 ml-4 list-disc text-red-400">
                {(missing_elements as string[]).map((el, i) => (
                  <li key={i}>{el}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    // Handoff event rendering
    if (step.kind === "handoff") {
      const { from_agent, to_agent, reason } = step.data as Record<
        string,
        unknown
      >;
      return (
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-purple-400 font-medium">
              {String(from_agent || "Agent")}
            </span>
            <ArrowRight size={14} className="text-muted-foreground" />
            <span className="text-cyan-400 font-medium">
              {String(to_agent || "Agent")}
            </span>
          </div>
          {reason && (
            <div className="text-muted-foreground italic">
              Reason: {String(reason)}
            </div>
          )}
        </div>
      );
    }

    // Progress event rendering
    if (step.kind === "progress") {
      const { action, feedback, percent } = step.data as Record<
        string,
        unknown
      >;
      return (
        <div className="space-y-2 text-sm">
          {action && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Action:</span>
              <span className="font-medium">{String(action)}</span>
            </div>
          )}
          {percent !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Progress:</span>
              <div className="flex-1 max-w-[200px] h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${Math.min(100, Number(percent))}%` }}
                />
              </div>
              <span className="text-xs">{Number(percent)}%</span>
            </div>
          )}
          {feedback && (
            <div className="text-muted-foreground">{String(feedback)}</div>
          )}
        </div>
      );
    }

    // Tool call event rendering
    if (step.kind === "tool_call") {
      const {
        tool_name,
        arguments: args,
        result,
      } = step.data as Record<string, unknown>;
      return (
        <div className="space-y-2 text-sm">
          {tool_name && (
            <div className="flex items-center gap-2">
              <Wrench size={12} className="text-blue-400" />
              <span className="font-mono text-blue-400">
                {String(tool_name)}
              </span>
            </div>
          )}
          {args && (
            <details className="mt-1">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground text-xs">
                Arguments
              </summary>
              <CodeBlock className="mt-1">
                <CodeBlockCode
                  code={JSON.stringify(args, null, 2)}
                  language="json"
                />
              </CodeBlock>
            </details>
          )}
          {result && (
            <details className="mt-1">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground text-xs">
                Result
              </summary>
              <div className="mt-1 p-2 bg-muted/20 rounded text-xs">
                {typeof result === "string" ? result : JSON.stringify(result)}
              </div>
            </details>
          )}
        </div>
      );
    }

    return null;
  };

  const richContent = renderRichContent();
  // Use rich content if available, otherwise fall back to standard display
  const hasRichContent = richContent !== null;

  return (
    <ChainOfThoughtStep isLast={isLast} defaultOpen={false}>
      <ChainOfThoughtTrigger leftIcon={getIcon()} className={getToneClass()}>
        {step.content}
      </ChainOfThoughtTrigger>
      {(hasRichContent || hasDetails) && (
        <ChainOfThoughtContent>
          {hasRichContent ? (
            richContent
          ) : (
            <>
              {outputContent != null && (
                <div className="mb-2 text-sm prose dark:prose-invert max-w-none">
                  <Markdown>{String(outputContent)}</Markdown>
                </div>
              )}
              <CodeBlock className="my-2">
                <CodeBlockCode
                  code={JSON.stringify(displayData, null, 2)}
                  language="json"
                />
              </CodeBlock>
            </>
          )}
        </ChainOfThoughtContent>
      )}
    </ChainOfThoughtStep>
  );
};
