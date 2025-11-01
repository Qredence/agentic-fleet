import { Button } from "@/components/ui/shadcn/button";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/__components/ui/chat-container";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/ui/custom/message";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/__components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/custom/prompt-suggestion";
import { SystemMessage } from "@/__components/ui/system-message";
import { cn } from "@/lib/utils";
import {
  ArrowUp,
  Copy,
  Globe,
  Mic,
  MoreHorizontal,
  Pencil,
  Plus,
  ThumbsDown,
  ThumbsUp,
  Trash,
} from "lucide-react";
import { useState } from "react";
import { useChatController } from "./useChatController";

export default function ChatPage() {
  const { health, messages, pending, error, send, conversationId } =
    useChatController();
  const [inputValue, setInputValue] = useState("");

  const disabled = health !== "ok" || !conversationId || pending;

  const handleSubmit = () => {
    if (inputValue.trim() && !disabled) {
      send(inputValue.trim());
      setInputValue("");
    }
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b px-4 py-3">
        <h1 className="text-2xl font-bold text-foreground">AgenticFleet</h1>
        <span
          className={cn(
            "text-xs",
            health === "ok"
              ? "text-green-500"
              : health === "down"
                ? "text-red-500"
                : "text-muted-foreground",
          )}
        >
          backend: {health}
        </span>
      </div>

      {/* Error Display */}
      {error && (
        <div className="shrink-0 px-4 py-2">
          <SystemMessage>{error}</SystemMessage>
        </div>
      )}

      {/* Chat Container */}
      <ChatContainerRoot className="relative flex-1 space-y-0 overflow-y-auto px-4 py-12">
        <ChatContainerContent className="space-y-12 px-4 py-12">
          {pending && messages.length === 0 && (
            <div className="flex justify-center py-8">
              <div className="text-muted-foreground text-sm">
                Starting conversation...
              </div>
            </div>
          )}
          {messages.length === 0 && !pending && (
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-0 md:px-6">
              <div className="text-center text-muted-foreground mb-4">
                <h2 className="text-xl font-semibold mb-2">Get started</h2>
                <p className="text-sm">
                  Choose a suggestion or type your own message
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                <PromptSuggestion
                  onClick={() => {
                    setInputValue("What can you help me with?");
                  }}
                >
                  What can you help me with?
                </PromptSuggestion>
                <PromptSuggestion
                  onClick={() => {
                    setInputValue("Explain how AgenticFleet works");
                  }}
                >
                  Explain how AgenticFleet works
                </PromptSuggestion>
                <PromptSuggestion
                  onClick={() => {
                    setInputValue("Show me an example workflow");
                  }}
                >
                  Show me an example workflow
                </PromptSuggestion>
              </div>
            </div>
          )}
          {messages.map((message, index) => {
            const isAssistant = message.role === "assistant";
            const isLastMessage = index === messages.length - 1;

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
                          onClick={() =>
                            navigator.clipboard.writeText(message.content)
                          }
                        >
                          <Copy />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Upvote" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <ThumbsUp />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Downvote" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <ThumbsDown />
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
                      <MessageAction tooltip="Edit" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <Pencil />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Delete" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                        >
                          <Trash />
                        </Button>
                      </MessageAction>
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                          onClick={() =>
                            navigator.clipboard.writeText(message.content)
                          }
                        >
                          <Copy />
                        </Button>
                      </MessageAction>
                    </MessageActions>
                  </div>
                )}
              </Message>
            );
          })}
        </ChatContainerContent>
      </ChatContainerRoot>

      {/* Prompt Input */}
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        <PromptInput
          isLoading={pending}
          value={inputValue}
          onValueChange={setInputValue}
          onSubmit={handleSubmit}
          disabled={disabled}
          className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
        >
          <div className="flex flex-col">
            <PromptInputTextarea
              placeholder={
                disabled
                  ? health === "checking"
                    ? "Connecting to backend..."
                    : "Waiting for connection..."
                  : "Ask anything"
              }
              className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
            />

            <PromptInputActions className="mt-5 flex w-full items-center justify-between gap-2 px-3 pb-3">
              <div className="flex items-center gap-2">
                <PromptInputAction tooltip="Add a new action">
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-9 rounded-full"
                    disabled={disabled}
                  >
                    <Plus size={18} />
                  </Button>
                </PromptInputAction>

                <PromptInputAction tooltip="Search">
                  <Button
                    variant="outline"
                    className="rounded-full"
                    disabled={disabled}
                  >
                    <Globe size={18} />
                    Search
                  </Button>
                </PromptInputAction>

                <PromptInputAction tooltip="More actions">
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-9 rounded-full"
                    disabled={disabled}
                  >
                    <MoreHorizontal size={18} />
                  </Button>
                </PromptInputAction>
              </div>
              <div className="flex items-center gap-2">
                <PromptInputAction tooltip="Voice input">
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-9 rounded-full"
                    disabled={disabled}
                  >
                    <Mic size={18} />
                  </Button>
                </PromptInputAction>

                <Button
                  size="icon"
                  disabled={disabled}
                  type="button"
                  onClick={handleSubmit}
                  className="size-9 rounded-full"
                >
                  {pending ? (
                    <span className="size-3 rounded-xs bg-white" />
                  ) : (
                    <ArrowUp size={18} />
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
