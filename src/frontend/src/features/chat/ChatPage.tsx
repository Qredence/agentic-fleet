import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/ui/chat-container";
import { Loader } from "@/components/ui/loader";
import { SystemMessage } from "@/components/ui/system-message";
import { MessageList } from "./MessageList";
import { PromptBar } from "./PromptBar";
import { useChatController } from "./useChatController";

export default function ChatPage() {
  const { health, messages, pending, error, send, conversationId } =
    useChatController();
  const disabled = health !== "ok" || !conversationId || pending;

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
              health === "ok" ? "#0a0" : health === "down" ? "#a00" : "#666",
          }}
        >
          backend: {health}
        </span>
      </div>

      {error && <SystemMessage>{error}</SystemMessage>}

      <ChatContainerRoot>
        <ChatContainerContent>
          {pending && <Loader />}
          <MessageList items={messages} />
        </ChatContainerContent>
      </ChatContainerRoot>

      <PromptBar disabled={disabled} onSend={send} />
    </div>
  );
}
