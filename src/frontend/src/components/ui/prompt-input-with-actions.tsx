import { cn } from "@/lib/utils";
import { Plus, Settings, Mic, Send } from "lucide-react";
import { useRef, useState } from "react";

export interface PromptInputWithActionsProps {
  onSendMessage?: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function PromptInputWithActions({
  onSendMessage,
  disabled = false,
  placeholder = "Message...",
  className,
}: PromptInputWithActionsProps) {
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && onSendMessage) {
      onSendMessage(message.trim());
      setMessage("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "48px";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "48px";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Handle image upload here
      // Image selected: file
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn("p-4", className)}>
      <div
        className="w-full rounded-3xl shadow-lg border border-border/60 overflow-hidden"
        style={{ backgroundColor: "rgb(48, 48, 48)" }}
      >
        <div className="flex flex-col w-full p-2 gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
            aria-label="Attach image"
          />

          {/* Textarea field */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full text-sm text-foreground outline-none placeholder:text-muted-foreground py-3 px-3 bg-transparent resize-none overflow-hidden"
            style={{ minHeight: "48px", maxHeight: "200px" }}
          />

          {/* Bottom row with action buttons */}
          <div className="flex items-center gap-2 px-2 pb-2">
            {/* Left action buttons */}
            <div className="flex items-center gap-2">
              {/* Attach image button */}
              <button
                type="button"
                onClick={handleImageClick}
                disabled={disabled}
                aria-label="Attach image"
                className="flex items-center justify-center w-8 h-8 rounded-full text-foreground hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="h-6 w-6" />
              </button>

              {/* Tools button */}
              <button
                type="button"
                disabled={disabled}
                aria-label="Tools"
                className="flex items-center gap-2 px-2 py-1.5 rounded-full text-xs font-medium text-foreground hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Settings className="h-4 w-4" />
                <span>Tools</span>
              </button>
            </div>

            {/* Right action buttons */}
            <div className="ml-auto flex items-center gap-2">
              {/* Voice record button */}
              <button
                type="button"
                disabled={disabled}
                aria-label="Record voice"
                className="flex items-center gap-2 px-2 py-1.5 rounded-full text-xs font-medium text-foreground hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Mic className="h-5 w-5" />
                <span>Record voice</span>
              </button>

              {/* Send button */}
              <button
                type="submit"
                disabled={!message.trim() || disabled}
                aria-label="Send message"
                className="flex items-center justify-center w-8 h-8 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  backgroundColor:
                    !message.trim() || disabled
                      ? "rgb(81, 81, 81)"
                      : "rgb(0, 0, 0)",
                  color: "rgb(255, 255, 255)",
                }}
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </form>
  );
}
