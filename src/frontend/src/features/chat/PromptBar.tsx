import { useState } from "react";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from "@/components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
import { Button } from "@/components/ui/button";

export function PromptBar(props: {
  disabled: boolean;
  onSend: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const send = () => {
    if (!input) return;
    props.onSend(input);
    setInput("");
  };
  return (
    <div style={{ marginTop: 12 }}>
      <PromptInput>
        <PromptInputTextarea
          placeholder="Type a message"
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
        />
        <PromptInputActions>
          <PromptInputAction tooltip="Send">
            <Button disabled={props.disabled || !input} onClick={send}>
              Send
            </Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>
      <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {["Summarize repository", "List open tasks", "Plan next steps"].map(
          (s, i) => (
            <PromptSuggestion key={i} onClick={() => setInput(s)}>
              {s}
            </PromptSuggestion>
          ),
        )}
      </div>
    </div>
  );
}
