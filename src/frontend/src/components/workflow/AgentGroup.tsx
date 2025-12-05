import React from "react";
import { Brain } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Loader } from "../prompt-kit/loader";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "../prompt-kit/reasoning";
import { ChainOfThought } from "../prompt-kit/chain-of-thought";
import { Message, MessageContent } from "../prompt-kit/message";
import { cn } from "@/lib/utils";
import { ChatStep } from "../ChatStep";
import type { AgentGroupProps } from "./types";
import {
  hasReasoningSteps,
  hasThoughtSteps,
  hasOutputSteps,
  getReasoningContent,
  getThoughtSteps,
  getOutputContent,
} from "./utils";

export const AgentGroup: React.FC<AgentGroupProps> = ({
  name,
  avatar,
  steps,
  isThinking,
}) => {
  const thoughtSteps = getThoughtSteps(steps);
  const showReasoning = hasReasoningSteps(steps);
  const showThoughts = hasThoughtSteps(steps);
  const showOutput = hasOutputSteps(steps);

  // If no meaningful content, don't render
  if (steps.length === 0) return null;

  return (
    <div
      className={cn(
        "border-l-2 pl-4 mb-4 transition-colors",
        isThinking ? "border-primary/50" : "border-muted",
      )}
    >
      {/* Agent header */}
      <div className="flex items-center gap-2 mb-3">
        <Avatar className="h-6 w-6">
          {avatar && <AvatarImage src={avatar} alt={name} />}
          <AvatarFallback className="text-xs bg-primary/10">
            {name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <span className="font-medium text-sm">{name}</span>
        {isThinking && <Loader variant="typing" size="sm" className="ml-2" />}
      </div>

      {/* Reasoning section (for GPT-5 extended reasoning) */}
      {showReasoning && (
        <div className="mb-3">
          <Reasoning isStreaming={isThinking}>
            <ReasoningTrigger className="text-xs">
              <Brain size={12} className="mr-1" />
              Reasoning
            </ReasoningTrigger>
            <ReasoningContent markdown className="text-sm">
              {getReasoningContent(steps)}
            </ReasoningContent>
          </Reasoning>
        </div>
      )}

      {/* Thought steps as ChainOfThought */}
      {showThoughts && thoughtSteps.length > 0 && (
        <div className="mb-3">
          <ChainOfThought>
            {thoughtSteps.map((step, index) => (
              <ChatStep
                key={step.id}
                step={step}
                isLast={index === thoughtSteps.length - 1}
              />
            ))}
          </ChainOfThought>
        </div>
      )}

      {/* Final output as Message */}
      {showOutput && (
        <div className="mt-2">
          <Message className="flex-col gap-1">
            <MessageContent markdown className="bg-secondary/50 text-sm">
              {getOutputContent(steps)}
            </MessageContent>
          </Message>
        </div>
      )}
    </div>
  );
};

export default AgentGroup;
