import { useEffect, useMemo } from "react";
import { Layout } from "./components/Layout";
import { MessageBubble } from "./components/MessageBubble";
import { InputBar } from "./components/InputBar";
import { useChat } from "./hooks/useChat";
import {
  ChatContainerRoot,
  ChatContainerContent,
  ChatContainerScrollAnchor,
} from "./components/prompt-kit/chat-container";
import { ScrollButton } from "./components/prompt-kit/scroll-button";
import { groupMessagesByAgent } from "./lib/messageUtils";

function App() {
  const {
    messages,
    sendMessage,
    createConversation,
    isLoading,
    currentReasoning,
    isReasoningStreaming,
    currentWorkflowPhase,
    cancelStreaming,
  } = useChat();

  useEffect(() => {
    createConversation();
  }, [createConversation]);

  // Group messages by agent for better visual separation
  const messageGroups = useMemo(
    () => groupMessagesByAgent(messages),
    [messages],
  );

  // Get reasoning for the last assistant message if streaming
  const getReasoningForMessage = (msgIndex: number, totalMessages: number) => {
    // Only show reasoning on the last message if currently streaming
    if (isReasoningStreaming && msgIndex === totalMessages - 1) {
      return currentReasoning;
    }
    return undefined;
  };

  // Flatten messages for indexing (for reasoning assignment)
  const flatMessageCount = messages.length;

  return (
    <Layout>
      <div className="flex-1 flex flex-col h-full relative overflow-hidden">
        <ChatContainerRoot className="flex-1 px-4 py-8 flex flex-col">
          <ChatContainerContent className="max-w-3xl mx-auto space-y-6 pb-4">
            {messages.length === 0 && !isLoading && (
              <div className="text-center text-muted-foreground mt-20">
                <h2 className="text-2xl font-semibold mb-2">
                  Welcome to Agentic Fleet
                </h2>
                <p>Start a conversation to begin.</p>
              </div>
            )}

            {messageGroups.map((group, groupIndex) => {
              return (
                <div
                  key={`${group.groupId}-${groupIndex}`}
                  className="space-y-2"
                >
                  {/* Agent switch indicator for non-first groups */}
                  {groupIndex > 0 &&
                    !group.isUserGroup &&
                    !messageGroups[groupIndex - 1].isUserGroup && (
                      <div className="flex items-center gap-2 px-4 py-1">
                        <div className="flex-1 h-px bg-muted/30" />
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50">
                          Agent switched
                        </span>
                        <div className="flex-1 h-px bg-muted/30" />
                      </div>
                    )}

                  {group.messages.map((msg, msgIndex) => {
                    // Calculate global message index for reasoning assignment
                    let globalIndex = 0;
                    for (let i = 0; i < groupIndex; i++) {
                      globalIndex += messageGroups[i].messages.length;
                    }
                    globalIndex += msgIndex;

                    const isLastMessage = globalIndex === flatMessageCount - 1;
                    const isFirstInGroup = msgIndex === 0;
                    const isLastInGroup =
                      msgIndex === group.messages.length - 1;
                    const showAvatar = isFirstInGroup;
                    const isGrouped = group.messages.length > 1;

                    return (
                      <MessageBubble
                        key={msg.id || msg.created_at}
                        role={msg.role}
                        content={msg.content}
                        steps={msg.steps}
                        author={msg.author}
                        reasoning={getReasoningForMessage(
                          globalIndex,
                          flatMessageCount,
                        )}
                        isReasoningStreaming={
                          isReasoningStreaming && isLastMessage
                        }
                        onCancelStreaming={
                          isLoading ? cancelStreaming : undefined
                        }
                        isStreaming={isLoading && isLastMessage}
                        workflowPhase={
                          msg.workflowPhase || currentWorkflowPhase
                        }
                        isWorkflowPlaceholder={msg.isWorkflowPlaceholder}
                        showAvatar={showAvatar}
                        isGrouped={isGrouped}
                        isFirstInGroup={isFirstInGroup}
                        isLastInGroup={isLastInGroup}
                      />
                    );
                  })}
                </div>
              );
            })}
          </ChatContainerContent>
          <ChatContainerScrollAnchor />
          <div className="sticky bottom-4 self-end mr-4 z-10">
            <ScrollButton />
          </div>
        </ChatContainerRoot>

        {/* Input Area */}
        <div className="w-full p-6 bg-background/80 backdrop-blur-sm border-t border-border">
          <div className="max-w-3xl mx-auto">
            <InputBar
              onSendMessage={sendMessage}
              disabled={isLoading}
              isStreaming={isLoading}
              onCancel={cancelStreaming}
              workflowPhase={currentWorkflowPhase}
            />
            <div className="text-center mt-4 text-xs text-muted-foreground">
              Agentic Fleet can make mistakes. Check important info.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default App;
