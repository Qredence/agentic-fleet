import { useMemo } from "react";
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
    selectConversation,
    conversationId,
    isConversationsLoading,
  } = useChat();

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
        <div className="flex-1 flex flex-col h-full min-h-0 relative overflow-hidden bg-gray-1000">
          <ChatContainerRoot className="flex-1 flex flex-col relative z-0 min-h-0">
            <ChatContainerContent
              className="flex-1 max-w-5xl md:max-w-6xl mx-auto w-full px-4 md:px-6 py-8 space-y-8 pb-40"
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
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center space-y-6"
                  role="status"
                >
                  <div className="w-24 h-24 rounded-3xl bg-linear-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mb-4 shadow-2xl shadow-blue-900/20 border border-white/5">
                    <span className="text-4xl">✨</span>
                  </div>
                  <div className="space-y-2 max-w-md">
                    <h2 className="text-3xl font-semibold tracking-tight text-gray-0">
                      Agentic Fleet
                    </h2>
                    <p className="text-gray-400 text-lg">
                      Your advanced AI agent orchestration platform.
                      <br />
                      Ready to solve complex tasks.
                    </p>
                  </div>
                </motion.div>
              ) : (
                <AnimatePresence mode="popLayout" initial={false}>
                  <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
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
                                className="flex items-center gap-4 px-4 py-2 opacity-50"
                              >
                                <div className="flex-1 h-px bg-linear-to-r from-transparent via-gray-700 to-transparent" />
                                <span className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">
                                  Agent Handoff
                                </span>
                                <div className="flex-1 h-px bg-linear-to-r from-transparent via-gray-700 to-transparent" />
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
            <div className="fixed bottom-24 right-8 z-20">
              <ScrollButton />
            </div>
          </ChatContainerRoot>

          {/* Input Area - Floating Glass Bar */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.3 }}
            className="absolute bottom-0 left-0 right-0 z-30"
          >
            <div className="glass-bar pb-6 pt-4 px-4">
              <div className="max-w-5xl md:max-w-6xl mx-auto px-0 md:px-2">
                <ChatInput
                  onSendMessage={sendMessage}
                  isStreaming={isLoading}
                  onCancel={cancelStreaming}
                  workflowPhase={currentWorkflowPhase}
                />
                <div className="text-center mt-3 text-[10px] uppercase tracking-wider text-gray-500">
                  Agentic Fleet v0.5 • AI Orchestration
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </Layout>
    </ErrorBoundary>
  );
}

export default App;
