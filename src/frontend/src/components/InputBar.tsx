import { useState, useRef, useEffect } from "react";
import {
  Paperclip,
  Send,
  ChevronDown,
  Lightbulb,
  Square,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReasoningEffort } from "@/lib/constants";

interface InputBarProps {
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

export const InputBar: React.FC<InputBarProps> = ({
  onSendMessage,
  disabled,
  onCancel,
  isStreaming,
  workflowPhase,
}) => {
  const [input, setInput] = useState("");
  const [thinkHarder, setThinkHarder] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isDisabled = disabled || isStreaming;

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (input.trim() && !isDisabled) {
      onSendMessage(input, {
        reasoning_effort: thinkHarder ? "maximal" : undefined,
      });
      setInput("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !isDisabled) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto relative">
      {/* Think harder toggle */}
      <div
        className={cn(
          "absolute -top-12 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-gray-900/80 backdrop-blur-sm border rounded-full px-4 py-1.5 text-sm cursor-pointer hover:bg-gray-800 transition-colors",
          thinkHarder
            ? "border-yellow-500/50 text-yellow-400"
            : "border-gray-800 text-gray-300",
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

      <div
        className={cn(
          "bg-gray-900 rounded-3xl p-2 border shadow-lg relative overflow-hidden transition-all duration-300",
          isStreaming
            ? "border-blue-500/50 shadow-blue-500/10"
            : "border-gray-800",
        )}
      >
        {/* Loading indicator bar at top when streaming */}
        {isStreaming && (
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-linear-to-r from-blue-500 via-purple-500 to-blue-500 animate-shimmer bg-size-[200%_100%]" />
        )}

        <div className="px-4 py-3">
          {/* Workflow phase indicator when streaming */}
          {isStreaming && workflowPhase && (
            <div className="flex items-center gap-2 mb-2 text-xs text-blue-400">
              <Loader2 size={12} className="animate-spin" />
              <span>{workflowPhase}</span>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isStreaming ? "Waiting for response..." : "Ask Anything..."
            }
            className={cn(
              "w-full bg-transparent text-white text-lg placeholder-gray-500 focus:outline-none resize-none min-h-7 max-h-[200px] transition-opacity",
              isDisabled && "opacity-50 cursor-not-allowed",
            )}
            disabled={isDisabled}
            rows={1}
          />
        </div>

        <div className="flex items-center justify-between px-2 pb-1 mt-2">
          <div
            className={cn(
              "flex items-center gap-2 transition-opacity",
              isDisabled && "opacity-50 pointer-events-none",
            )}
          >
            <button
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Attach file"
              aria-label="Attach file"
              disabled={isDisabled}
              onClick={() => {
                /* TODO: implement file attachment */
              }}
            >
              <Paperclip size={20} />
            </button>
            <button
              className="flex items-center gap-1 px-3 py-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-full transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isDisabled}
              aria-label="Select mode"
              aria-haspopup="listbox"
              onClick={() => {
                /* TODO: implement mode selection */
              }}
            >
              <span>Auto</span>
              <ChevronDown size={14} />
            </button>
          </div>

          {isStreaming ? (
            <button
              onClick={onCancel}
              className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-full font-medium hover:bg-red-700 transition-colors"
              title="Stop generating"
            >
              <Square size={16} className="fill-current" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              onClick={() => handleSubmit()}
              disabled={!input.trim() || isDisabled}
              className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-full font-medium hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={16} />
              <span>Send</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
