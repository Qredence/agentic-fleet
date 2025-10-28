import { useState } from "react";
import { Button } from "@/components/ui/shadcn/button";
import { Send, Loader2 } from "lucide-react";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
} from "@/components/ui/prompt-kit";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export const ChatInput = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message...",
  className = ""
}: ChatInputProps) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = async () => {
    if (!inputValue.trim() || disabled || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSendMessage(inputValue.trim());
      setInputValue("");
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={`w-full ${className}`}>
      <PromptInput
        isLoading={isSubmitting}
        value={inputValue}
        onValueChange={setInputValue}
        onSubmit={handleSubmit}
        className="w-full"
      >
        <PromptInputTextarea
          placeholder={disabled ? "Processing..." : placeholder}
          disabled={disabled || isSubmitting}
          onKeyDown={handleKeyDown}
          className="min-h-[44px] max-h-32"
        />

        <PromptInputActions className="pt-2">
          <Button
            onClick={handleSubmit}
            disabled={!inputValue.trim() || disabled || isSubmitting}
            size="sm"
            className="ml-auto"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="sr-only">Send message</span>
          </Button>
        </PromptInputActions>
      </PromptInput>
    </div>
  );
};
