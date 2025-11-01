import { memo, useMemo } from "react";
import { FixedSizeList as List } from "react-window";
import { ChatMessage } from "./ChatMessage";
import type { AgentType, Message } from "@/lib/types";
import { mapRoleToAgent } from "@/lib/agent-utils";

interface MessageListProps {
  messages: Array<Message & { receivedAt: string }>;
  timeFormatter: Intl.DateTimeFormat;
  _isAtBottom: boolean;
  _onScrollToBottom: () => void;
}

interface MessageRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    messages: Array<
      Message & {
        receivedAt: string;
        agent: string;
        formattedTimestamp: string;
      }
    >;
  };
}

const MessageRow = memo(({ index, style, data }: MessageRowProps) => {
  const msg = data.messages[index];
  if (!msg) return null;

  return (
    <div style={style}>
      <ChatMessage
        message={msg.content}
        agent={msg.agent as AgentType}
        timestamp={msg.formattedTimestamp}
        isNew={msg.isNew}
        isStreaming={msg.isStreaming}
      />
    </div>
  );
});

MessageRow.displayName = "MessageRow";

export const VirtualizedMessageList = memo(
  ({ messages, timeFormatter }: MessageListProps) => {
    const mappedMessages = useMemo(() => {
      return messages.map((msg) => ({
        ...msg,
        agent: mapRoleToAgent(msg.role, msg.actor),
        formattedTimestamp: timeFormatter.format(new Date(msg.receivedAt)),
      }));
    }, [messages, timeFormatter]);

    // Use virtual scrolling for 50+ messages, otherwise use regular list
    const shouldVirtualize = mappedMessages.length >= 50;

    if (!shouldVirtualize) {
      return (
        <>
          {mappedMessages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg.content}
              agent={msg.agent as AgentType}
              timestamp={msg.formattedTimestamp}
              isNew={msg.isNew}
              isStreaming={msg.isStreaming}
            />
          ))}
        </>
      );
    }

    return (
      <List
        height={window.innerHeight - 200} // Approximate height
        itemCount={mappedMessages.length}
        itemSize={100} // Estimated item height
        itemData={{ messages: mappedMessages }}
        width="100%"
      >
        {MessageRow}
      </List>
    );
  },
);

VirtualizedMessageList.displayName = "VirtualizedMessageList";
