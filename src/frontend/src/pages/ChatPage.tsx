import { ChainOfThought } from "@/components/chat/ChainOfThought";
import { LoadingIndicator } from "@/components/chat/LoadingIndicator";
import { ConversationsSidebar } from "@/components/chat/ConversationsSidebar";
import { Button } from "@/components/ui/button";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/ui/chat-container";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { MessageList } from "@/components/chat/MessageList";
import { useConversationInitialization } from "@/hooks/useConversationInitialization";
import { useChatStore } from "@/stores/chatStore";
import { ArrowUp, CircleStop, Menu } from "lucide-react";
import { useState } from "react";

/** Main chat page component */
export function ChatPage() {
  const {
    messages,
    currentStreamingMessage,
    currentAgentId,
    currentStreamingMessageId,
    currentStreamingTimestamp,
    currentReasoningContent,
    currentReasoningStreaming,
    orchestratorMessages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    cancelStreaming,
  } = useChatStore();
  const { initializing } = useConversationInitialization();

  const [inputMessage, setInputMessage] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Conversation initialization moved to hook

  const handleSend = async () => {
    if (!inputMessage.trim() || isLoading || !conversationId) {
      return;
    }

    const message = inputMessage.trim();
    setInputMessage("");
    await sendMessage(message);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <ConversationsSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden md:ml-[280px]">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden"
              aria-label="Toggle sidebar"
            >
              <Menu size={20} />
            </Button>
            <h1 className="text-lg font-semibold">AgenticFleet Chat</h1>
            {conversationId && (
              <span className="text-xs text-muted-foreground">
                ({conversationId.slice(0, 8)}...)
              </span>
            )}
          </div>
          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-1 text-sm text-destructive">
              {error}
            </div>
          )}
        </header>

        {/* Messages area */}
        <ChatContainerRoot className="relative flex-1 space-y-0 overflow-y-auto px-4 py-12">
          <ChatContainerContent className="space-y-12 px-4 py-12 mx-auto max-w-[700px]">
            {/* Render orchestrator messages (chain-of-thought) */}
            {orchestratorMessages.length > 0 && (
              <div className="mx-auto w-full max-w-[700px]">
                <ChainOfThought messages={orchestratorMessages} />
              </div>
            )}

            {/* Render messages */}
            {messages.length === 0 &&
              !currentStreamingMessage &&
              !isLoading && (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <h2 className="mb-2 text-xl font-semibold">
                      Welcome to AgenticFleet
                    </h2>
                    <p className="text-muted-foreground">
                      Start a conversation by typing a message below.
                    </p>
                  </div>
                </div>
              )}

            <MessageList
              messages={messages}
              currentStreamingMessage={currentStreamingMessage}
              currentStreamingMessageId={currentStreamingMessageId}
              currentStreamingTimestamp={currentStreamingTimestamp}
              currentAgentId={currentAgentId}
              currentReasoningContent={currentReasoningContent}
              currentReasoningStreaming={currentReasoningStreaming}
            />
            {/* Loading indicator */}
            {isLoading && !currentStreamingMessage && (
              <div className="mx-auto w-full max-w-[700px]">
                <LoadingIndicator />
              </div>
            )}
          </ChatContainerContent>
        </ChatContainerRoot>

        {/* Input area */}
        <div className="inset-x-0 bottom-0 mx-auto w-full max-w-[700px] shrink-0 px-3 pb-3 md:px-5 md:pb-5">
          <PromptInput
            isLoading={isLoading}
            value={inputMessage}
            onValueChange={setInputMessage}
            onSubmit={handleSend}
            disabled={isLoading || !conversationId}
            className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-sm"
          >
            <div className="flex flex-col">
              <PromptInputTextarea
                placeholder={
                  initializing || !conversationId
                    ? "Initializing conversation..."
                    : "Ask anything"
                }
                className="min-h-11 pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
                data-testid="chat-input"
              />

              <PromptInputActions className="mt-5 flex w-full items-center justify-between gap-2 px-3 pb-3">
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-9 rounded-full"
                    aria-label="Cancel streaming"
                    data-testid="cancel-button"
                    onClick={cancelStreaming}
                    disabled={!isLoading && !currentStreamingMessageId}
                  >
                    <CircleStop size={18} />
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="icon"
                    disabled={
                      !inputMessage.trim() || isLoading || !conversationId
                    }
                    onClick={handleSend}
                    className="size-9 rounded-full"
                    aria-label="Send message"
                    data-testid="send-button"
                  >
                    {!isLoading ? (
                      <ArrowUp size={18} />
                    ) : (
                      <span className="size-3 rounded-xs bg-white" />
                    )}
                  </Button>
                </div>
              </PromptInputActions>
            </div>
          </PromptInput>
        </div>
      </div>
    </div>
  );
}
