import React, { useState } from "react";
import { Rocket, ChevronDown, Zap, Users, Sparkles } from "lucide-react";
import { Select } from "@openai/apps-sdk-ui/components/Select";

const ModeOptionDescription = ({ children }: { children: React.ReactNode }) => (
  <div className="font-normal text-secondary py-px text-[0.935em] leading-[1.45]">
    {children}
  </div>
);

const modes = [
  {
    value: "auto",
    label: "Auto",
    description: (
      <ModeOptionDescription>
        Automatically determines the best path for your query
      </ModeOptionDescription>
    ),
  },
  {
    value: "fast",
    label: "Fast Path",
    description: (
      <ModeOptionDescription>
        Quick responses with minimal processing
      </ModeOptionDescription>
    ),
  },
  {
    value: "agentic",
    label: "Agentic Fleet",
    description: (
      <ModeOptionDescription>
        Multi-agent collaboration for complex tasks
      </ModeOptionDescription>
    ),
  },
];

interface InputBarProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

export const InputBar: React.FC<InputBarProps> = ({
  onSendMessage,
  disabled,
}) => {
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("auto");

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto relative">
      {/* Think harder toggle */}
      <div
        className="absolute -top-12 left-1/2 -translate-x-1/2 flex items-center gap-2 backdrop-blur-sm rounded-full px-4 py-1.5 text-sm cursor-pointer transition-colors hover:opacity-80"
        style={{
          backgroundColor: "var(--color-surface-secondary)",
          color: "var(--color-text-secondary)",
          border: "1px solid var(--gray-200)",
        }}
      >
        <Sparkles size={14} />
        <span>Think harder</span>
      </div>

      {/* Scroll down indicator (optional, based on UI) */}
      <div
        className="absolute -top-12 right-0 p-2 rounded-full cursor-pointer transition-colors hover:opacity-80"
        style={{
          backgroundColor: "var(--color-surface-secondary)",
          color: "var(--color-text-tertiary)",
          border: "1px solid var(--gray-200)",
        }}
      >
        <ChevronDown size={16} />
      </div>

      <div
        className="rounded-[32px] p-2 shadow-lg relative overflow-hidden"
        style={{
          backgroundColor: "var(--color-surface-secondary)",
          border: "1px solid var(--gray-200)",
        }}
      >
        <div className="px-4 py-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Anything"
            className="w-full bg-transparent text-lg focus:outline-none"
            style={{ color: "var(--color-text)" }}
            disabled={disabled}
          />
        </div>

        <div className="flex items-center justify-between px-2 pb-1 mt-2">
          <div className="flex items-center gap-2">
            <Select
              value={mode}
              options={modes}
              placeholder="Select mode..."
              align="start"
              listMinWidth={260}
              variant="ghost"
              size="sm"
              onChange={({ value }) => setMode(value)}
              TriggerStartIcon={
                mode === "auto" ? Rocket : mode === "fast" ? Zap : Users
              }
              triggerClassName="font-semibold"
              optionClassName="font-semibold"
            />
          </div>

          <button
            onClick={() => handleSubmit()}
            disabled={!input.trim() || disabled}
            className="flex items-center justify-center gap-2 h-9 px-3.5 rounded-full text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: "var(--gray-900)",
              color: "var(--gray-0)",
            }}
          >
            <div className="flex gap-0.5 items-center">
              <div
                className="w-0.5 h-3 rounded-full animate-pulse"
                style={{ backgroundColor: "var(--gray-0)" }}
              ></div>
              <div
                className="w-0.5 h-2 rounded-full animate-pulse delay-75"
                style={{ backgroundColor: "var(--gray-0)" }}
              ></div>
              <div
                className="w-0.5 h-4 rounded-full animate-pulse delay-150"
                style={{ backgroundColor: "var(--gray-0)" }}
              ></div>
            </div>
            <span>Submit</span>
          </button>
        </div>
      </div>
    </div>
  );
};
