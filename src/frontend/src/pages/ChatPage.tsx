import { ChainOfThought } from "@/components/chat/ChainOfThought";
import { LoadingIndicator } from "@/components/chat/LoadingIndicator";
import { StructuredMessageContent } from "@/components/chat/StructuredMessageContent";
import { Button } from "@/components/ui/button";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/ui/chat-container";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageAvatar,
} from "@/components/ui/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { createConversation } from "@/lib/api/chat";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { ArrowUp, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";

/** Main chat page component */
export function ChatPage() {
  const {
    messages,
    currentStreamingMessage,
    currentAgentId,
    currentStreamingMessageId,
    currentStreamingTimestamp,
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
            id:
              currentStreamingMessageId ??
              `streaming-${currentStreamingTimestamp ?? Date.now()}`,
            role: "assistant" as const,
            content: currentStreamingMessage,
            agentId: currentAgentId,
            createdAt: currentStreamingTimestamp ?? Date.now(),
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
        <ChatContainerContent className="space-y-12 px-4 py-12 mx-auto max-w-[700px]">
          {/* Render orchestrator messages (chain-of-thought) */}
          {orchestratorMessages.length > 0 && (
            <div className="mx-auto w-full max-w-[700px]">
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
            const isUser = message.role === "user";
            const isAssistant = message.role === "assistant";
            const isStreamingMessage =
              Boolean(currentStreamingMessageId) &&
              message.id === currentStreamingMessageId;
            const isLastMessage = index === allMessages.length - 1;
            const isFinalAssistantMessage =
              isAssistant && isLastMessage && !isStreamingMessage;
            const timestamp = new Date(message.createdAt).toLocaleTimeString(
              [],
              {
                hour: "2-digit",
                minute: "2-digit",
              },
            );
            const avatarFallback = isUser
              ? "Y"
              : (message.agentId?.slice(0, 2).toUpperCase() ?? "AI");

            return (
              <Message
                key={message.id}
                className={cn(
                  "group w-full max-w-[700px] items-start gap-3 md:gap-4",
                  isUser ? "ml-auto flex-row-reverse" : "mr-auto",
                )}
              >
                <MessageAvatar
                  src=""
                  alt={isUser ? "User avatar" : "Assistant avatar"}
                  fallback={avatarFallback}
                  className={cn(
                    "border border-border",
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground",
                  )}
                />

                <div
                  className={cn(
                    "flex min-w-0 flex-1 flex-col gap-2",
                    isUser ? "items-end text-right" : "items-start text-left",
                  )}
                >
                  <div
                    className={cn(
                      "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
                      isUser ? "justify-end" : "justify-start",
                    )}
                  >
                    <span className="font-medium text-foreground">
                      {isUser ? "You" : "Assistant"}
                    </span>
                    {isAssistant && message.agentId && (
                      <span className="text-muted-foreground">
                        · {message.agentId}
                      </span>
                    )}
                    <span>{timestamp}</span>
                  </div>

                  <div
                    className={cn(
                      "flex w-full",
                      isUser ? "justify-end" : "justify-start",
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[90%] rounded-3xl px-5 py-3 text-sm leading-relaxed shadow-none sm:max-w-[75%]",
                        isUser
                          ? "bg-[#F4F4F5] text-foreground border border-transparent"
                          : "bg-transparent text-foreground border border-transparent",
                      )}
                    >
                      <StructuredMessageContent
                        content={message.content}
                        isStreaming={isStreamingMessage}
                        forcePlain={isFinalAssistantMessage}
                        className={cn(
                          "max-w-none leading-relaxed",
                          isUser
                            ? "[--tw-prose-body:theme(colors.primary.foreground)] [--tw-prose-headings:theme(colors.primary.foreground)] prose-strong:text-primary-foreground"
                            : "[--tw-prose-body:theme(colors.foreground)] [--tw-prose-headings:theme(colors.foreground)]",
                        )}
                      />
                    </div>
                  </div>

                  {isStreamingMessage && (
                    <span className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary" />
                      {message.agentId
                        ? `Streaming from ${message.agentId}`
                        : "Streaming…"}
                    </span>
                  )}

                  <MessageActions
                    className={cn(
                      "flex gap-1 text-xs text-muted-foreground transition-opacity duration-150",
                      isUser ? "justify-end" : "justify-start",
                      isLastMessage || isUser
                        ? "opacity-100"
                        : "opacity-0 group-hover:opacity-100",
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
                    {isAssistant && (
                      <>
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
                      </>
                    )}
                  </MessageActions>
                </div>
              </Message>
            );
          })}

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
