import { Button } from "@/components/ui/button";
import { ChatContainer } from "@/components/ui/chat-container";
import { Message } from "@/components/ui/message";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { useEffect, useState } from "react";

function useHealth() {
  const [status, setStatus] = useState<"ok" | "down" | "checking">("checking");
  useEffect(() => {
    fetch("/v1/health")
      .then((r) => r.json())
      .then(() => setStatus("ok"))
      .catch(() => setStatus("down"));
  }, []);
  return status;
}

export default function App() {
  const [convId, setConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<
    Array<{ role: "user" | "assistant"; content: string }>
  >([]);
  const status = useHealth();
  const disabled = status !== "ok" || !convId;

  useEffect(() => {
    fetch("/v1/conversations", { method: "POST" })
      .then((r) => r.json())
      .then((b) => setConvId(b.id));
  }, []);

  const send = async () => {
    if (!convId || !input) return;
    const text = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    const resp = await fetch("/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: convId, message: text }),
    });
    const body = await resp.json();
    const reply = String(body.message ?? "");
    setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
  };

  return (
    <div style={{ maxWidth: 880, margin: "2rem auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <h1 style={{ fontFamily: "ui-sans-serif, system-ui" }}>AgenticFleet</h1>
        <span
          style={{
            fontSize: 12,
            color:
              status === "ok" ? "#0a0" : status === "down" ? "#a00" : "#666",
          }}
        >
          backend: {status}
        </span>
      </div>

      <ChatContainer>
        {messages.map((m, idx) => (
          <Message key={idx} role={m.role} content={m.content} />
        ))}
      </ChatContainer>

      <div style={{ marginTop: 12 }}>
        <PromptInput>
          <PromptInputTextarea
            placeholder="Type a message"
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
          />
          <PromptInputActions>
            <PromptInputAction tooltip="Send">
              <Button disabled={disabled || !input} onClick={send}>
                Send
              </Button>
            </PromptInputAction>
          </PromptInputActions>
        </PromptInput>
      </div>
    </div>
  );
}
