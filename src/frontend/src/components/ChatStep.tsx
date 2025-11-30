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
} from "lucide-react";
import type { ConversationStep } from "../api/types";
import {
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
} from "./prompt-kit/chain-of-thought";
import { CodeBlock, CodeBlockCode } from "./prompt-kit/code-block";
import { Markdown } from "./prompt-kit/markdown";

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
        return <CircleDashed size={14} />;
      default:
        if (step.type === "error") return <AlertCircle size={14} />;
        if (step.type === "thought" || step.type === "agent_thought")
          return <Brain size={14} />;
        if (step.type === "agent_start") return <Play size={14} />;
        if (step.type === "agent_complete") return <CheckSquare size={14} />;
        if (step.type === "agent_output") return <MessageSquare size={14} />;
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

  return (
    <ChainOfThoughtStep isLast={isLast} defaultOpen={false}>
      <ChainOfThoughtTrigger leftIcon={getIcon()} className={getToneClass()}>
        {step.content}
      </ChainOfThoughtTrigger>
      {hasDetails && (
        <ChainOfThoughtContent>
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
        </ChainOfThoughtContent>
      )}
    </ChainOfThoughtStep>
  );
};
