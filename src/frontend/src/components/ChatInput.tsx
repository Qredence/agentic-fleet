"use client";

import { useState } from "react";
import {
  Paperclip,
  ArrowUp,
  Square,
  Lightbulb,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from "@/components/prompt-kit/prompt-input";
import { Loader } from "@/components/prompt-kit/loader";
import type { ReasoningEffort } from "@/lib/constants";

interface ChatInputProps {
  onSendMessage: (
    content: string,
    options?: { reasoning_effort?: ReasoningEffort },
  ) => void;
  disabled?: boolean;
  onCancel?: () => void;
  isStreaming?: boolean;
  /** Current workflow phase to display (e.g., "Routing...", "Executing...") */
  workflowPhase?: string;
}

export function ChatInput({
  onSendMessage,
  disabled,
  onCancel,
  isStreaming,
  workflowPhase,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [thinkHarder, setThinkHarder] = useState(false);
  const isDisabled = disabled || isStreaming;

  const handleSubmit = () => {
    if (input.trim() && !isDisabled) {
      onSendMessage(input, {
        reasoning_effort: thinkHarder ? "maximal" : undefined,
      });
      setInput("");
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto relative">
      {/* Think harder toggle */}
      <div
        className={cn(
          "absolute -top-12 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-secondary/80 backdrop-blur-sm border rounded-full px-4 py-1.5 text-sm cursor-pointer hover:bg-secondary transition-colors",
          thinkHarder
            ? "border-yellow-500/50 text-yellow-400"
            : "border-border text-muted-foreground",
          isDisabled && "opacity-50 pointer-events-none",
        )}
        role="button"
        tabIndex={isDisabled ? -1 : 0}
        aria-label={`Think harder - extended reasoning mode (${thinkHarder ? "enabled" : "disabled"})`}
        aria-pressed={thinkHarder}
        onClick={() => {
          if (!isDisabled) {
            setThinkHarder(!thinkHarder);
          }
        }}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !isDisabled) {
            e.preventDefault();
            setThinkHarder(!thinkHarder);
          }
        }}
      >
        <Lightbulb size={14} className={thinkHarder ? "fill-current" : ""} />
        <span>Think harder</span>
        {thinkHarder && (
          <span className="text-xs bg-yellow-500/20 px-1.5 py-0.5 rounded">
            ON
          </span>
        )}
      </div>

      <PromptInput
        isLoading={isStreaming}
        value={input}
        onValueChange={setInput}
        onSubmit={handleSubmit}
        disabled={isDisabled}
        className={cn(
          "border-input bg-card relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-lg transition-all duration-300",
          isStreaming && "border-blue-500/50 shadow-blue-500/10",
        )}
      >
        {/* Loading indicator bar at top when streaming */}
        {isStreaming && (
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 animate-shimmer bg-[length:200%_100%]" />
        )}

        <div className="flex flex-col">
          {/* Workflow phase indicator when streaming */}
          {isStreaming && workflowPhase && (
            <div className="flex items-center gap-2 px-4 pt-2 text-xs text-blue-400">
              <Loader variant="circular" size="sm" />
              <span>{workflowPhase}</span>
            </div>
          )}

          <PromptInputTextarea
            placeholder={
              isStreaming ? "Waiting for response..." : "Ask anything..."
            }
            className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
          />

          <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 p-2">
            <div className="flex items-center gap-1">
              <PromptInputAction tooltip="Attach file">
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full text-muted-foreground hover:text-foreground"
                  disabled={isDisabled}
                >
                  <Paperclip size={18} />
                </Button>
              </PromptInputAction>

              <PromptInputAction tooltip="Select mode">
                <Button
                  variant="ghost"
                  size="sm"
                  className="rounded-full text-muted-foreground hover:text-foreground gap-1"
                  disabled={isDisabled}
                >
                  <span>Auto</span>
                  <ChevronDown size={14} />
                </Button>
              </PromptInputAction>
            </div>

            <div className="flex items-center gap-2">
              {isStreaming ? (
                <Button
                  onClick={onCancel}
                  variant="destructive"
                  size="sm"
                  className="rounded-full gap-2"
                >
                  <Square size={14} className="fill-current" />
                  <span>Stop</span>
                </Button>
              ) : (
                <Button
                  size="icon"
                  disabled={!input.trim() || isDisabled}
                  onClick={handleSubmit}
                  className="size-9 rounded-full"
                >
                  <ArrowUp size={18} />
                </Button>
              )}
            </div>
          </PromptInputActions>
        </div>
      </PromptInput>
    </div>
  );
}
