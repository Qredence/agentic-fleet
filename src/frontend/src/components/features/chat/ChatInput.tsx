import {
  PromptBox,
  PromptBoxHandle,
} from "@/components/ui/custom/prompt-input";
import { useCallback, useRef, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput = ({ onSendMessage, disabled }: ChatInputProps) => {
  const promptBoxRef = useRef<PromptBoxHandle | null>(null);

  const submitMessage = useCallback((): void => {
    const message = promptBoxRef.current?.getValue().trim() ?? "";
    if (!message) {
      return;
    }
    onSendMessage(message);
    promptBoxRef.current?.clear();
  }, [onSendMessage]);

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      submitMessage();
    },
    [submitMessage],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submitMessage();
      }
    },
    [submitMessage],
  );

  return (
    <form onSubmit={handleSubmit}>
      <PromptBox
        ref={promptBoxRef}
        disabled={disabled}
        onKeyDown={handleKeyDown}
      />
    </form>
  );
};
