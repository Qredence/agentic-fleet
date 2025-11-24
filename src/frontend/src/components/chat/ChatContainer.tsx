/**
 * ChatContainer Component
 * Main container for the chat interface
 */

import { MessageList } from "./MessageList";
import { PromptInputArea } from "./PromptInputArea";
import { useChatStore } from "../../stores/chatStore";
import { useStreamingChat } from "../../hooks/useStreamingChat";

export function ChatContainer() {
  const {
    conversations,
    currentConversationId,
    addMessage,
    createConversation,
    setStreamingState,
    clearStreaming,
    streamingContent,
    streamingAgentId,
    streamingReasoning,
  } = useChatStore();

  const currentConversation =
    conversations.find((c) => c.id === currentConversationId) || null;

  const { isStreaming, orchestratorThought, currentAgentId, sendMessage } =
    useStreamingChat({
      onMessageComplete: (content: string) => {
        if (currentConversationId) {
          addMessage(currentConversationId, "assistant", content);
        }
        clearStreaming();
      },
      onReasoningDelta: (reasoning: string) => {
        setStreamingState({ reasoning });
      },
      onDelta: (content: string, agentId?: string) => {
        setStreamingState({ content, agentId });
      },
      onError: (error) => {
        console.error("Streaming error:", error);
        clearStreaming();
      },
    });

  const handleSendMessage = async (message: string) => {
    try {
      let conversationId = currentConversationId;

      // Auto-create conversation if none exists
      if (!conversationId) {
        const newConversation = await createConversation("New Conversation");
        conversationId = newConversation.id;
      }

      clearStreaming();

      // Add user message immediately
      addMessage(conversationId, "user", message);

      // Start streaming assistant response
      await sendMessage(conversationId, message);
    } catch (error) {
      console.error("Failed to send message:", error);
      // Consider showing user-facing error notification
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-default bg-surface px-6 py-4">
        <h1 className="heading-md">
          {currentConversation?.title || "New Conversation"}
        </h1>
        <p className="text-xs text-secondary mt-1">
          {currentConversation?.messages.length || 0} messages
        </p>
      </div>

      {/* Messages */}
      <MessageList
        messages={currentConversation?.messages || []}
        streamingContent={streamingContent}
        orchestratorThought={orchestratorThought}
        streamingAgentId={currentAgentId || streamingAgentId}
        streamingReasoning={streamingReasoning}
        isStreaming={isStreaming}
      />

      {/* Input */}
      <PromptInputArea
        onSendMessage={handleSendMessage}
        isLoading={isStreaming}
        placeholder="Type your message..."
      />
    </div>
  );
}
