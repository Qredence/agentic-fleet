import { PromptBox } from "@/components/ui/custom/prompt-input";
import { useRef } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput = ({ onSendMessage, disabled }: ChatInputProps) => {
  const formRef = useRef<HTMLFormElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const textarea = formRef.current?.querySelector("textarea") as HTMLTextAreaElement;
    if (textarea && textarea.value.trim()) {
      onSendMessage(textarea.value.trim());
      textarea.value = "";
      textarea.style.height = "48px";
    }
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit}>
      <PromptBox disabled={disabled} />
    </form>
  );
};
