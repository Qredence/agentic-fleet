/**
 * ChatInput Component - Responsive Message Input
 * 
 * Features:
 * - Responsive sizing for mobile/tablet/desktop
 * - Proper touch targets on mobile (44px minimum)
 * - Flexible textarea with proper constraints
 */

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
          className="min-h-[44px] max-h-32 text-sm sm:text-base resize-none"
        />

        <PromptInputActions className="pt-2 flex justify-end">
          <Button
            onClick={handleSubmit}
            disabled={!inputValue.trim() || disabled || isSubmitting}
            size="sm"
            className="h-9 w-9 sm:h-10 sm:w-auto sm:px-4"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="sr-only sm:not-sr-only sm:ml-2">Send</span>
          </Button>
        </PromptInputActions>
      </PromptInput>
    </div>
  );
};
