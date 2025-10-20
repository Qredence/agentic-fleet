import { memo } from "react";
import type { Message } from "@/lib/use-fastapi-chat";
import { MessageComponent, LoadingMessage, ErrorMessage } from "./agenticfleet-chatbot";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  error: Error | null;
}

const MessageList = memo(({ messages, isLoading, error }: MessageListProps) => (
  <>
    {messages.map((message) => (
      <MessageComponent key={message.id} message={message} />
    ))}
    {isLoading && <LoadingMessage />}
    {error && <ErrorMessage error={error} />}
  </>
));

MessageList.displayName = "MessageList";

export default MessageList;
