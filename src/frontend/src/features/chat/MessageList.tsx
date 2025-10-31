import { CodeBlock } from "@/components/ui/code-block";
import { Markdown } from "@/components/ui/markdown";
import { Message } from "@/components/ui/message";

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
        <Message
          key={message.id}
          role={message.role}
          content={
            <Markdown
              content={message.content}
              components={{ code: CodeBlock }}
            />
          }
        />
      ))}
    </div>
  );
}
