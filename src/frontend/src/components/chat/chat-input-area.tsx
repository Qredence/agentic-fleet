import { PromptInput, PromptInputTextarea } from "./prompt-input";
import { ChatInputControls } from "./chat-input-controls";
import type { ExecutionMode } from "@/lib/constants";

export type ChatInputAreaProps = {
  isLoading: boolean;
  prompt: string;
  onPromptChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  executionMode: ExecutionMode;
  enableGepa: boolean;
  showTrace: boolean;
  showRawReasoning: boolean;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onToggleGepa: () => void;
  onToggleTrace: () => void;
  onToggleRawReasoning: () => void;
};

export function ChatInputArea({
  isLoading,
  prompt,
  onPromptChange,
  onSubmit,
  onCancel,
  executionMode,
  enableGepa,
  showTrace,
  showRawReasoning,
  onExecutionModeChange,
  onToggleGepa,
  onToggleTrace,
  onToggleRawReasoning,
}: ChatInputAreaProps) {
  return (
    <div className="z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5">
      <div className="mx-auto max-w-3xl">
        <PromptInput
          isLoading={isLoading}
          value={prompt}
          onValueChange={onPromptChange}
          onSubmit={onSubmit}
          className="relative z-10 w-full p-0"
        >
          <div className="flex flex-col">
            <PromptInputTextarea
              placeholder="Ask anything..."
              className="min-h-12 pt-4 pl-4 pr-12 text-base leading-normal bg-transparent border-0 shadow-none focus-visible:ring-0"
            />

            <ChatInputControls
              isLoading={isLoading}
              prompt={prompt}
              executionMode={executionMode}
              enableGepa={enableGepa}
              showTrace={showTrace}
              showRawReasoning={showRawReasoning}
              onExecutionModeChange={onExecutionModeChange}
              onToggleGepa={onToggleGepa}
              onToggleTrace={onToggleTrace}
              onToggleRawReasoning={onToggleRawReasoning}
              onSubmit={onSubmit}
              onCancel={onCancel}
            />
          </div>
        </PromptInput>
      </div>
    </div>
  );
}
