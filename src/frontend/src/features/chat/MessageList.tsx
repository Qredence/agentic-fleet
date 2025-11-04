import { Message, MessageContent } from "@/components/ui/message";

export function MessageList(props: {
  items: Array<{
    id: string | number;
    role: "user" | "assistant" | "system";
    content: string;
  }>;
}) {
  return (
    <div>
      {props.items.map((message) => (
        <Message key={message.id}>
          <MessageContent markdown={true}>{message.content}</MessageContent>
        </Message>
      ))}
    </div>
  );
}
