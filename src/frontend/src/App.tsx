import { useEffect, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Layout } from "./components/Layout";
import { ChatMessage } from "./components/ChatMessage";
import { ChatInput } from "./components/ChatInput";
import {
  ErrorBoundary,
  MessageErrorBoundary,
} from "./components/ErrorBoundary";
import { useChat } from "./hooks/useChat";
import {
  ChatContainerRoot,
  ChatContainerContent,
  ChatContainerScrollAnchor,
} from "./components/prompt-kit/chat-container";
import { ScrollButton } from "./components/prompt-kit/scroll-button";
import { groupMessagesByAgent } from "./lib/messageUtils";
import { containerVariants, itemVariants } from "./lib/animations";
import { ChatAreaSkeleton } from "./components/MessageSkeleton";
import { TypingIndicator } from "./components/AnimatedMessage";

function App() {
  const {
    messages,
    sendMessage,
    createConversation,
    isLoading,
    isInitializing,
    currentReasoning,
    isReasoningStreaming,
    currentWorkflowPhase,
    currentAgent,
    cancelStreaming,
    conversations,
    loadConversations,
    selectConversation,
    conversationId,
    isConversationsLoading,
  } = useChat();

  useEffect(() => {
    loadConversations();
    createConversation();
  }, [loadConversations, createConversation]);

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
    <ErrorBoundary>
      <Layout
        onNewChat={createConversation}
        conversations={conversations}
        currentConversationId={conversationId}
        onSelectConversation={selectConversation}
        isConversationsLoading={isConversationsLoading}
      >
        <div className="flex-1 flex flex-col h-full relative overflow-hidden">
          <ChatContainerRoot className="flex-1 px-4 py-8 flex flex-col">
            <ChatContainerContent
              className="max-w-3xl mx-auto space-y-6 pb-4"
              aria-live="polite"
              aria-atomic="false"
              aria-busy={isLoading}
            >
              {/* Show skeleton during initial load */}
              {isInitializing ? (
                <ChatAreaSkeleton />
              ) : messages.length === 0 && !isLoading ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="text-center text-muted-foreground mt-20"
                  role="status"
                >
                  <h2 className="text-2xl font-semibold mb-2">
                    Welcome to Agentic Fleet
                  </h2>
                  <p>Start a conversation to begin.</p>
                </motion.div>
              ) : (
                <AnimatePresence mode="popLayout" initial={false}>
                  <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-6"
                  >
                    {messageGroups.map((group, groupIndex) => {
                      return (
                        <motion.div
                          key={`${group.groupId}-${groupIndex}`}
                          variants={itemVariants}
                          layout
                          className="space-y-2"
                        >
                          {/* Agent switch indicator for non-first groups */}
                          {groupIndex > 0 &&
                            !group.isUserGroup &&
                            !messageGroups[groupIndex - 1].isUserGroup && (
                              <motion.div
                                initial={{ opacity: 0, scaleX: 0 }}
                                animate={{ opacity: 1, scaleX: 1 }}
                                transition={{ duration: 0.3 }}
                                className="flex items-center gap-2 px-4 py-1"
                              >
                                <div className="flex-1 h-px bg-muted/30" />
                                <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50">
                                  Agent switched
                                </span>
                                <div className="flex-1 h-px bg-muted/30" />
                              </motion.div>
                            )}

                          {group.messages.map((msg, msgIndex) => {
                            // Calculate global message index for reasoning assignment
                            let globalIndex = 0;
                            for (let i = 0; i < groupIndex; i++) {
                              globalIndex += messageGroups[i].messages.length;
                            }
                            globalIndex += msgIndex;

                            const isLastMessage =
                              globalIndex === flatMessageCount - 1;
                            const isFirstInGroup = msgIndex === 0;
                            const isLastInGroup =
                              msgIndex === group.messages.length - 1;
                            const showAvatar = isFirstInGroup;
                            const isGrouped = group.messages.length > 1;

                            return (
                              <motion.div
                                key={msg.id || msg.created_at}
                                layout
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{
                                  type: "spring",
                                  stiffness: 400,
                                  damping: 30,
                                }}
                              >
                                <MessageErrorBoundary>
                                  <ChatMessage
                                    id={msg.id}
                                    role={msg.role}
                                    content={msg.content}
                                    steps={msg.steps}
                                    author={msg.author}
                                    agent_id={msg.agent_id}
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
                                    showAvatar={showAvatar}
                                    isGrouped={isGrouped}
                                    isFirstInGroup={isFirstInGroup}
                                    isLastInGroup={isLastInGroup}
                                  />
                                </MessageErrorBoundary>
                              </motion.div>
                            );
                          })}
                        </motion.div>
                      );
                    })}

                    {/* Show typing indicator when streaming but no content yet */}
                    {isLoading &&
                      currentAgent &&
                      messages.length > 0 &&
                      messages[messages.length - 1]?.isWorkflowPlaceholder && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                        >
                          <TypingIndicator agentName={currentAgent} />
                        </motion.div>
                      )}
                  </motion.div>
                </AnimatePresence>
              )}
            </ChatContainerContent>
            <ChatContainerScrollAnchor />
            <div className="sticky bottom-4 self-end mr-4 z-10">
              <ScrollButton />
            </div>
          </ChatContainerRoot>

          {/* Input Area */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.3 }}
            className="w-full p-6 bg-background/80 backdrop-blur-sm border-t border-border"
          >
            <div className="max-w-3xl mx-auto">
              <ChatInput
                onSendMessage={sendMessage}
                isStreaming={isLoading}
                onCancel={cancelStreaming}
                workflowPhase={currentWorkflowPhase}
              />
              <div className="text-center mt-4 text-xs text-muted-foreground">
                Agentic Fleet can make mistakes. Check important info.
              </div>
            </div>
          </motion.div>
        </div>
      </Layout>
    </ErrorBoundary>
  );
}

export default App;
