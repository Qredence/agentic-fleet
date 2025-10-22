import { cn } from "@/lib/utils";
import { Send } from "lucide-react";
import { useState } from "react";

export interface PromptInputWithActionsProps {
  onSendMessage?: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function PromptInputWithActions({
  onSendMessage,
  disabled = false,
  placeholder = "Message the agents...",
  className,
}: PromptInputWithActionsProps) {
  const [message, setMessage] = useState("");
  const [tags, setTags] = useState([
    { id: 1, label: "yolo mode", active: true },
    { id: 2, label: "memory", active: false },
  ]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && onSendMessage) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn("p-4", className)}>
      <div className="w-full bg-card rounded-3xl shadow-sm border border-border overflow-hidden">
        <div className="flex flex-col w-full p-3 gap-2">
          {/* Input field */}
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full text-sm text-foreground outline-none placeholder:text-muted-foreground py-1 px-1 bg-transparent"
          />

          {/* Bottom row with tags and send button */}
          <div className="flex items-center justify-between w-full">
            {/* Tags container */}
            <div className="flex gap-2">
              {tags.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() =>
                    setTags(tags.map((t) => (t.id === tag.id ? { ...t, active: !t.active } : t)))
                  }
                  className={cn(
                    "flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border transition-smooth",
                    tag.active
                      ? "bg-accent text-accent-foreground border-border hover:bg-accent/80"
                      : "bg-card text-muted-foreground border-border hover:bg-muted"
                  )}
                >
                  <span>{tag.label}</span>
                </button>
              ))}
            </div>

            {/* Send button */}
            <button
              type="submit"
              disabled={!message.trim() || disabled}
              aria-label="Send message"
              className={cn(
                "flex items-center justify-center px-4 py-1.5 rounded-full text-xs font-semibold transition-smooth",
                !message.trim() || disabled
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              )}
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
