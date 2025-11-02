import { useEffect, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/ui/chat-container";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/ui/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowUp, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { createConversation } from "@/lib/api/chat";
import { LoadingIndicator } from "@/components/chat/LoadingIndicator";
import { ChainOfThought } from "@/components/chat/ChainOfThought";

/** Main chat page component */
export function ChatPage() {
  const {
    messages,
    currentStreamingMessage,
    currentAgentId,
    orchestratorMessages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    setConversationId,
    setError,
  } = useChatStore();

  const [inputMessage, setInputMessage] = useState("");

  // Initialize conversation on mount
  useEffect(() => {
    if (!conversationId) {
      createConversation()
        .then((conv) => {
          setConversationId(conv.id);
        })
        .catch((err) => {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to create conversation",
          );
        });
    }
  }, [conversationId, setConversationId, setError]);

  const handleSend = async () => {
    if (!inputMessage.trim() || isLoading || !conversationId) {
      return;
    }

    const message = inputMessage.trim();
    setInputMessage("");
    await sendMessage(message);
  };

  const allMessages = [
    ...messages,
    ...(currentStreamingMessage
      ? [
          {
            id: `streaming-${Date.now()}`,
            role: "assistant" as const,
            content: currentStreamingMessage,
            agentId: currentAgentId,
          },
        ]
      : []),
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
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
        <ChatContainerContent className="space-y-12 px-4 py-12">
          {/* Render orchestrator messages (chain-of-thought) */}
          {orchestratorMessages.length > 0 && (
            <div className="mx-auto w-full max-w-3xl">
              <ChainOfThought messages={orchestratorMessages} />
            </div>
          )}

          {/* Render messages */}
          {allMessages.length === 0 && !isLoading && (
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

          {allMessages.map((message, index) => {
            const isAssistant = message.role === "assistant";
            const isLastMessage = index === allMessages.length - 1;
            const isStreamingMessage = message.id.startsWith("streaming-");

            return (
              <Message
                key={message.id}
                className={cn(
                  "mx-auto flex w-full max-w-3xl flex-col gap-2 px-0 md:px-6",
                  isAssistant ? "items-start" : "items-end",
                )}
              >
                {isAssistant ? (
                  <div className="group flex w-full flex-col gap-0">
                    <MessageContent
                      className="text-foreground prose w-full flex-1 rounded-lg bg-transparent p-0"
                      markdown
                    >
                      {message.content}
                    </MessageContent>
                    {message.agentId && (
                      <div className="text-xs text-muted-foreground mt-1">
                        Agent: {message.agentId}
                      </div>
                    )}
                    {isStreamingMessage && (
                      <div className="text-xs text-muted-foreground mt-1">
                        Streaming...
                      </div>
                    )}
                    <MessageActions
                      className={cn(
                        "-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100",
                        isLastMessage && "opacity-100",
                      )}
                    >
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <Copy size={16} />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Upvote" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <ThumbsUp size={16} />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Downvote" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <ThumbsDown size={16} />
                        </Button>
                      </MessageAction>
                    </MessageActions>
                  </div>
                ) : (
                  <div className="group flex flex-col items-end gap-1">
                    <MessageContent className="bg-muted text-primary max-w-[85%] rounded-3xl px-5 py-2.5 sm:max-w-[75%]">
                      {message.content}
                    </MessageContent>
                    <MessageActions
                      className={cn(
                        "flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100",
                      )}
                    >
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <Copy size={16} />
                        </Button>
                      </MessageAction>
                    </MessageActions>
                  </div>
                )}
              </Message>
            );
          })}

          {/* Loading indicator */}
          {isLoading && !currentStreamingMessage && (
            <div className="mx-auto w-full max-w-3xl">
              <LoadingIndicator />
            </div>
          )}
        </ChatContainerContent>
      </ChatContainerRoot>

      {/* Input area */}
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
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
                !conversationId
                  ? "Initializing conversation..."
                  : "Ask anything"
              }
              className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
            />

            <PromptInputActions className="mt-5 flex w-full items-center justify-between gap-2 px-3 pb-3">
              <div className="flex items-center gap-2">
                {/* Left side actions can be added here */}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="icon"
                  disabled={
                    !inputMessage.trim() || isLoading || !conversationId
                  }
                  onClick={handleSend}
                  className="size-9 rounded-full"
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
  );
}
