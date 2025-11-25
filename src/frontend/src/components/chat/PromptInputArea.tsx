"use client";

import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { ArrowUp, Square } from "lucide-react";
import { useState } from "react";

interface PromptInputAreaProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function PromptInputArea({
  onSendMessage,
  isLoading = false,
  disabled = false,
  placeholder = "Ask me anything...",
}: PromptInputAreaProps) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (!input.trim() || isLoading || disabled) return;
    onSendMessage(input);
    setInput("");
  };

  return (
    <div className="border-t border-default bg-surface p-4">
      <PromptInput
        value={input}
        onValueChange={setInput}
        isLoading={isLoading}
        onSubmit={handleSubmit}
        className="w-full"
      >
        <PromptInputTextarea placeholder={placeholder} disabled={disabled} />
        <PromptInputActions className="justify-end pt-2">
          <PromptInputAction
            tooltip={isLoading ? "Stop generation" : "Send message"}
          >
            <Button
              variant="default"
              size="icon"
              className="h-8 w-8 rounded-full"
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading || disabled}
            >
              {isLoading ? (
                <Square className="size-5 fill-current" />
              ) : (
                <ArrowUp className="size-5" />
              )}
            </Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>
    </div>
  );
}
