import React, { useState } from "react";
import { Button } from "@/components/ui/shadcn/button";
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

import { useChatController } from "../../../features/chat";

// Import consolidated chat components directly
import { ChatInput } from "./ChatInput";
import { EnhancedMessageList } from "./EnhancedMessageList";

// Simple system message component for now
const SystemMessage: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
    {children}
  </div>
);

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

  const handleSendMessage = (message: string) => {
    if (message.trim() && !disabled) {
      send(message.trim());
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !pending && (
          <div className="text-center py-12 text-muted-foreground">
            <p>No messages yet</p>
            <p className="text-sm mt-1">
              Start a conversation to see messages here
            </p>
          </div>
        )}

        {/* Use the consolidated MessageList component */}
        <EnhancedMessageList
          messages={messages}
          conversationId={conversationId || ""}
          className="space-y-4"
        />
      </div>

      {/* Input */}
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        {/* Use the consolidated ChatInput component */}
        <ChatInput
          disabled={disabled}
          placeholder={
            disabled
              ? health === "checking"
                ? "Connecting to backend..."
                : "Waiting for connection..."
              : "Ask anything"
          }
          onMessageSent={handleSendMessage}
          className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
        />

        {/* Fallback input if ChatInput doesn't work */}
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-lg border p-2"
            disabled={disabled}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
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
      </div>
    </div>
  );
}
