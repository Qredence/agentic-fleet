import { Send } from "lucide-react";
import { useState } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput = ({ onSendMessage, disabled }: ChatInputProps) => {
  const [message, setMessage] = useState("");
  const [tags, setTags] = useState([
    { id: 1, label: "fast mode", active: true },
    { id: 2, label: "memory", active: false },
  ]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
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
    <form onSubmit={handleSubmit} className="p-4">
      <div className="w-full rounded-3xl glass shadow-lg border border-border/60 overflow-hidden">
        <div className="flex flex-col w-full p-3 gap-2 justify-center items-start" style={{ height: "88px" }}>
          {/* Input field */}
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message the agents..."
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
                  className={`flex items-center gap-1 rounded-full text-xs font-semibold border transition-smooth ${
                    tag.active
                      ? "bg-accent text-accent-foreground border-border hover:bg-accent/80 py-2 px-3"
                      : "bg-card text-muted-foreground border-border hover:bg-muted py-1.5 px-3"
                  }`}
                  style={{
                    height: "auto",
                    alignSelf: "stretch",
                  }}
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
              className={`flex items-center justify-center px-4 rounded-full text-xs font-semibold transition-smooth ${
                !message.trim() || disabled
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
              style={{ height: "auto", alignSelf: "stretch" }}
            >
              <Send className="h-3.5 w-3.5 text-primary-foreground" />
            </button>
          </div>
        </div>
      </div>
    </form>
  );
};
