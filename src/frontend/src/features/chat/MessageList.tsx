import { CodeBlock } from "@/components/ui/code-block";
import { Markdown } from "@/components/ui/markdown";
import { Message } from "@/components/ui/message";

export function MessageList(props: {
  items: Array<{ role: "user" | "assistant" | "system"; content: string }>;
}) {
  return (
    <div>
      {props.items.map((m, i) => (
        <Message
          key={i}
          role={m.role}
          content={
            <Markdown content={m.content} components={{ code: CodeBlock }} />
          }
        />
      ))}
    </div>
  );
}
