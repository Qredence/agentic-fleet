import { Square, ArrowUp, Sparkles, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui";
import { PromptInputActions, PromptInputAction } from "./prompt-input";
import { ExecutionModeSelector } from "./execution-mode-selector";
import { ToggleButton } from "./toggle-button";
import type { ExecutionMode } from "@/lib/constants";

export type ChatInputControlsProps = {
  isLoading: boolean;
  prompt: string;
  executionMode: ExecutionMode;
  enableGepa: boolean;
  showTrace: boolean;
  showRawReasoning: boolean;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onToggleGepa: () => void;
  onToggleTrace: () => void;
  onToggleRawReasoning: () => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function ChatInputControls({
  isLoading,
  prompt,
  executionMode,
  enableGepa,
  showTrace,
  showRawReasoning,
  onExecutionModeChange,
  onToggleGepa,
  onToggleTrace,
  onToggleRawReasoning,
  onSubmit,
  onCancel,
}: ChatInputControlsProps) {
  return (
    <PromptInputActions className="mt-1 flex w-full items-center justify-between gap-2 px-3 pb-3">
      <div className="flex shrink-0 items-center gap-1.5">
        <ExecutionModeSelector
          value={executionMode}
          onChange={onExecutionModeChange}
        />

        <div className="h-4 w-px bg-border/50 mx-1" />

        <ToggleButton
          value={enableGepa}
          onChange={onToggleGepa}
          icon={Sparkles}
          label="GEPA"
          tooltipTitle="GEPA Optimization"
          tooltipDescription={
            enableGepa
              ? "Enabled: Gradient-based prompt adaptation"
              : "Disabled: Standard optimization"
          }
          iconClassName={enableGepa ? "fill-current" : undefined}
        />

        <ToggleButton
          value={showTrace}
          onChange={onToggleTrace}
          label="Tracing"
          tooltipTitle="Tracing"
          tooltipDescription={
            showTrace ? "Hide execution steps" : "Show execution steps"
          }
        />

        <ToggleButton
          value={showRawReasoning}
          onChange={onToggleRawReasoning}
          icon={BrainCircuit}
          tooltipTitle="Raw Reasoning"
          tooltipDescription={
            !showTrace
              ? "Enable Trace first to see reasoning"
              : showRawReasoning
                ? "Hide raw model reasoning"
                : "Show raw model reasoning"
          }
          disabled={!showTrace}
          size="icon"
        />
      </div>

      {isLoading ? (
        <PromptInputAction tooltip="Stop">
          <Button
            variant="destructive"
            size="icon"
            className="size-9 rounded-full shadow-md hover:shadow-lg transition-all duration-200"
            onClick={onCancel}
            aria-label="Stop streaming"
          >
            <Square className="size-4 fill-current" />
          </Button>
        </PromptInputAction>
      ) : (
        <Button
          variant="secondary"
          size="icon"
          disabled={!prompt.trim() || isLoading}
          onClick={onSubmit}
          className="size-9 rounded-full shadow-md hover:shadow-lg transition-all duration-200"
          aria-label="Send message"
        >
          <ArrowUp size={18} />
        </Button>
      )}
    </PromptInputActions>
  );
}
