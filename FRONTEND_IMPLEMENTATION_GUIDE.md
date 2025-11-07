# Frontend Refactoring Implementation Guide

This document provides step-by-step code implementations for the optimization recommendations.

## Technology Stack

- **Frontend**: React 19 + TypeScript + Vite
- **UI Components**: shadcn@canary (latest) + Radix UI primitives
- **Backend**: FastAPI with Server-Sent Events (SSE) streaming
- **State Management**: Zustand
- **Styling**: Tailwind CSS v4
- **Testing**: Vitest + React Testing Library

**Important**: Use `shadcn@canary` for the latest component patterns:

```bash
npx shadcn@canary add [component-name]
```

---

## Phase 1: Extract Streaming Logic

### Step 1: Create `useStreamingMessage` Hook

**File**: `src/features/chat/hooks/useStreamingMessage.ts`

```typescript
import { useCallback } from "react";
import type { ChatMessage } from "@/types/chat";

interface StreamingMessageState {
  currentMessage: string;
  currentAgentId?: string;
  currentMessageId?: string;
  currentTimestamp?: number;
}

interface UseStreamingMessageReturn {
  handleDelta: (delta: string, agentId?: string) => void;
  handleAgentComplete: (agentId: string, content: string) => void;
  handleCompleted: () => void;
  createStreamingMessage: () => ChatMessage | null;
  resetStreaming: () => void;
}

/**
 * Custom hook for managing streaming message state and transitions.
 * Encapsulates the complex logic of handling SSE deltas and agent completions.
 */
export function useStreamingMessage(
  state: StreamingMessageState,
  onStateChange: (updates: Partial<StreamingMessageState>) => void,
  onMessageCreate: (message: ChatMessage) => void,
): UseStreamingMessageReturn {
  const handleDelta = useCallback(
    (delta: string, agentId?: string) => {
      const timestamp = state.currentTimestamp || Date.now();

      onStateChange({
        currentMessage: state.currentMessage + delta,
        currentAgentId: agentId || state.currentAgentId,
        currentMessageId: state.currentMessageId || `streaming-${timestamp}`,
        currentTimestamp: timestamp,
      });
    },
    [state, onStateChange],
  );

  const handleAgentComplete = useCallback(
    (agentId: string, content: string) => {
      const messageContent =
        state.currentAgentId === agentId ? state.currentMessage : content;

      if (messageContent) {
        const message: ChatMessage = {
          id: `assistant-${state.currentTimestamp || Date.now()}`,
          role: "assistant",
          content: messageContent,
          createdAt: state.currentTimestamp || Date.now(),
          agentId,
        };
        onMessageCreate(message);
      }

      onStateChange({
        currentMessage: "",
        currentAgentId: undefined,
        currentMessageId: undefined,
        currentTimestamp: undefined,
      });
    },
    [state, onMessageCreate, onStateChange],
  );

  const handleCompleted = useCallback(() => {
    if (state.currentMessage) {
      const message: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: state.currentMessage,
        createdAt: state.currentTimestamp || Date.now(),
        agentId: state.currentAgentId,
      };
      onMessageCreate(message);
    }

    onStateChange({
      currentMessage: "",
      currentAgentId: undefined,
      currentMessageId: undefined,
      currentTimestamp: undefined,
    });
  }, [state, onMessageCreate, onStateChange]);

  const createStreamingMessage = useCallback((): ChatMessage | null => {
    if (!state.currentMessage) return null;

    return {
      id: state.currentMessageId || `streaming-${state.currentTimestamp}`,
      role: "assistant",
      content: state.currentMessage,
      agentId: state.currentAgentId,
      createdAt: state.currentTimestamp || Date.now(),
    };
  }, [state]);

  const resetStreaming = useCallback(() => {
    onStateChange({
      currentMessage: "",
      currentAgentId: undefined,
      currentMessageId: undefined,
      currentTimestamp: undefined,
    });
  }, [onStateChange]);

  return {
    handleDelta,
    handleAgentComplete,
    handleCompleted,
    createStreamingMessage,
    resetStreaming,
  };
}
```

### Step 2: Create `useConversationInitialization` Hook

**File**: `src/features/chat/hooks/useConversationInitialization.ts`

```typescript
import { useEffect } from "react";
import { createConversation } from "@/lib/api/chat";

interface UseConversationInitializationOptions {
  onSuccess?: (conversationId: string) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

/**
 * Custom hook for initializing a conversation on component mount.
 * Handles error states and success callbacks.
 */
export function useConversationInitialization(
  options: UseConversationInitializationOptions = {},
) {
  const { onSuccess, onError, enabled = true } = options;

  useEffect(() => {
    if (!enabled) return;

    let isMounted = true;

    const initializeConversation = async () => {
      try {
        const conversation = await createConversation();
        if (isMounted) {
          onSuccess?.(conversation.id);
        }
      } catch (error) {
        if (isMounted) {
          onError?.(
            error instanceof Error
              ? error
              : new Error("Failed to create conversation"),
          );
        }
      }
    };

    initializeConversation();

    return () => {
      isMounted = false;
    };
  }, [enabled, onSuccess, onError]);
}
```

### Step 3: FastAPI SSE Integration with Custom Hooks

**File**: `src/lib/api/fastapi.ts`

```typescript
import type { SSEEvent } from "@/types/chat";

/**
 * Parse SSE events from FastAPI StreamingResponse.
 * FastAPI sends events in format: data: {"type": "...", ...}
 */
export function parseSSEEvent(line: string): SSEEvent | null {
  if (!line.startsWith("data: ")) return null;

  try {
    const jsonStr = line.slice(6); // Remove 'data: ' prefix
    const data = JSON.parse(jsonStr);

    // Convert snake_case from FastAPI to camelCase for frontend
    return {
      type: data.type,
      delta: data.delta,
      agentId: data.agent_id, // Convert from snake_case
      error: data.error,
      message: data.message,
      kind: data.kind,
      content: data.content,
      reasoning: data.reasoning,
    };
  } catch (err) {
    console.warn("Failed to parse SSE event:", line, err);
    return null;
  }
}

/**
 * Stream chat responses from FastAPI backend.
 * Handles SSE connection and event parsing.
 */
export async function streamFromFastAPI(
  endpoint: string,
  body: Record<string, any>,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || "FastAPI request failed");
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("Response body is null");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const event = parseSSEEvent(line.trim());
        if (event) onEvent(event);
      }
    }
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error("Unknown error"));
  }
}
```

### Step 4: Update `useChatStore` to Use These Hooks

**File**: `src/stores/chatStore.ts` (simplified excerpt)

```typescript
import { useStreamingMessage } from "@/features/chat/hooks/useStreamingMessage";

export const useChatStore = create<ChatStore>((set, get) => {
  // Initialize streaming hook with store setters
  const streamingUtils = useStreamingMessage(
    {
      currentMessage: "",
      currentAgentId: undefined,
      currentMessageId: undefined,
      currentTimestamp: undefined,
    },
    (updates) => {
      set((state) => ({
        ...state,
        ...updates,
      }));
    },
    (message) => {
      set((state) => ({
        messages: [...state.messages, message],
      }));
    },
  );

  return {
    // ... existing state and actions

    // Use the streaming utilities in callbacks
    sendMessage: async (message: string) => {
      // ... existing logic
      await streamChatResponse(conversationId, message, {
        onDelta: streamingUtils.handleDelta,
        onAgentComplete: streamingUtils.handleAgentComplete,
        onCompleted: streamingUtils.handleCompleted,
        // ... other callbacks
      });
    },
  };
});
```

---

## Phase 2: Decompose ChatPage Component

### Step 1: Extract `ChatInput` Component

**File**: `src/components/chat/ChatInput/ChatInput.tsx`

```typescript
import { forwardRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { ArrowUp } from "lucide-react";
import type { ComponentProps } from "react";

interface ChatInputProps extends Omit<ComponentProps<"textarea">, "onChange"> {
  isLoading?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

/**
 * ChatInput component handles message input and submission.
 * Encapsulates input behavior and styling.
 */
export const ChatInput = forwardRef<HTMLTextAreaElement, ChatInputProps>(
  (
    {
      isLoading = false,
      onSubmit,
      value,
      onChange,
      disabled = false,
      placeholder = "Ask anything",
      ...props
    },
    ref
  ) => {
    const handleSubmit = useCallback(async () => {
      if (!value.trim() || isLoading || disabled) return;

      const message = value.trim();
      onChange("");
      await onSubmit(message);
    }, [value, isLoading, disabled, onChange, onSubmit]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    };

    return (
      <PromptInput
        isLoading={isLoading}
        value={value}
        onValueChange={onChange}
        onSubmit={handleSubmit}
        disabled={disabled}
        className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-sm"
      >
        <div className="flex flex-col">
          <PromptInputTextarea
            ref={ref}
            placeholder={
              disabled ? "Initializing conversation..." : placeholder
            }
            className="min-h-11 pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
            onKeyDown={handleKeyDown}
            disabled={disabled}
            {...props}
          />

          <PromptInputActions className="mt-5 flex w-full items-center justify-between gap-2 px-3 pb-3">
            <div className="flex items-center gap-2">
              {/* Left side actions placeholder */}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="icon"
                disabled={!value.trim() || isLoading || disabled}
                onClick={handleSubmit}
                className="size-9 rounded-full"
                aria-label="Send message"
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
    );
  }
);

ChatInput.displayName = "ChatInput";
```

### Step 2: Extract `MessageList` Component

**File**: `src/components/chat/MessageList/MessageList.tsx`

```typescript
import { useMemo } from "react";
import { Message } from "@/components/ui/message";
import { MessageListItem } from "./MessageListItem";
import type { ChatMessage } from "@/types/chat";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  currentReasoningContent?: string;
  currentReasoningStreaming?: boolean;
}

/**
 * MessageList component renders all messages in a conversation.
 * Handles empty state, loading indicators, and message rendering.
 */
export function MessageList({
  messages,
  isLoading = false,
  currentReasoningContent,
  currentReasoningStreaming,
}: MessageListProps) {
  const displayMessages = useMemo(
    () => messages.map((msg) => ({ key: msg.id, message: msg })),
    [messages]
  );

  if (displayMessages.length === 0 && !isLoading) {
    return (
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
    );
  }

  return (
    <div className="space-y-12 px-4 py-12 mx-auto max-w-[700px]">
      {displayMessages.map(({ key, message }, index) => (
        <MessageListItem
          key={key}
          message={message}
          isLastMessage={index === displayMessages.length - 1}
          reasoningContent={
            message.role === "assistant" ? currentReasoningContent : undefined
          }
          reasoningStreaming={currentReasoningStreaming}
        />
      ))}

      {isLoading && displayMessages.length === 0 && (
        <div className="mx-auto w-full max-w-[700px]">
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary" />
            <span className="text-sm text-muted-foreground">Processing...</span>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Step 3: Extract `MessageListItem` Component

**File**: `src/components/chat/MessageList/MessageListItem.tsx`

```typescript
import { useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageAvatar,
} from "@/components/ui/message";
import { ReasoningDisplay } from "../ReasoningDisplay";
import { StructuredMessageContent } from "../StructuredMessageContent";
import { Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/types/chat";

interface MessageListItemProps {
  message: ChatMessage;
  isLastMessage?: boolean;
  reasoningContent?: string;
  reasoningStreaming?: boolean;
}

/**
 * MessageListItem component renders a single message with all metadata.
 * Memoized to prevent unnecessary re-renders.
 */
export const MessageListItem = ({
  message,
  isLastMessage = false,
  reasoningContent,
  reasoningStreaming,
}: MessageListItemProps) => {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  const timestamp = useMemo(
    () =>
      new Date(message.createdAt).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    [message.createdAt]
  );

  const avatarFallback = useMemo(
    () => (isUser ? "Y" : message.agentId?.slice(0, 2).toUpperCase() ?? "AI"),
    [isUser, message.agentId]
  );

  return (
    <Message
      className={cn(
        "group w-full max-w-[700px] items-start gap-3 md:gap-4",
        isUser ? "ml-auto flex-row-reverse" : "mr-auto"
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
            : "bg-secondary text-secondary-foreground"
        )}
      />

      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col gap-2",
          isUser ? "items-end text-right" : "items-start text-left"
        )}
      >
        <div
          className={cn(
            "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
            isUser ? "justify-end" : "justify-start"
          )}
        >
          <span className="font-medium text-foreground">
            {isUser ? "You" : "Assistant"}
          </span>
          {isAssistant && message.agentId && (
            <span className="text-muted-foreground">· {message.agentId}</span>
          )}
          <span>{timestamp}</span>
        </div>

        <div
          className={cn(
            "flex w-full flex-col gap-3",
            isUser ? "items-end" : "items-start"
          )}
        >
          {isAssistant && (message.reasoning || reasoningContent) && (
            <div className="w-full">
              <ReasoningDisplay
                content={reasoningContent || message.reasoning}
                isStreaming={reasoningStreaming}
                triggerText="Model reasoning"
                defaultOpen={reasoningStreaming}
              />
            </div>
          )}

          <div
            className={cn(
              "max-w-[90%] rounded-3xl px-5 py-3 text-sm leading-relaxed shadow-none sm:max-w-[75%]",
              isUser
                ? "bg-[#F4F4F5] text-foreground border border-transparent"
                : "bg-transparent text-foreground border border-transparent"
            )}
          >
            <StructuredMessageContent
              content={message.content}
              className={cn(
                "max-w-none leading-relaxed",
                isUser
                  ? "[--tw-prose-body:var(--color-primary-foreground)] [--tw-prose-headings:var(--color-primary-foreground)] prose-strong:text-primary-foreground"
                  : "[--tw-prose-body:var(--color-foreground)] [--tw-prose-headings:var(--color-foreground)]"
              )}
            />
          </div>
        </div>

        <MessageActions
          className={cn(
            "flex gap-1 text-xs text-muted-foreground transition-opacity duration-150",
            isUser ? "justify-end" : "justify-start",
            isLastMessage ? "opacity-100" : "opacity-0 group-hover:opacity-100"
          )}
        >
          <MessageAction tooltip="Copy" delayDuration={100}>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full"
              onClick={() => navigator.clipboard.writeText(message.content)}
            >
              <Copy size={16} />
            </Button>
          </MessageAction>
          {isAssistant && (
            <>
              <MessageAction tooltip="Upvote" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <ThumbsUp size={16} />
                </Button>
              </MessageAction>
              <MessageAction tooltip="Downvote" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <ThumbsDown size={16} />
                </Button>
              </MessageAction>
            </>
          )}
        </MessageActions>
      </div>
    </Message>
  );
};

MessageListItem.displayName = "MessageListItem";
```

### Step 4: Refactor `ChatPage` Component

**File**: `src/pages/ChatPage.tsx` (simplified)

```typescript
import { useEffect, useRef, useState } from "react";
import { ChatInput } from "@/components/chat/ChatInput/ChatInput";
import { MessageList } from "@/components/chat/MessageList/MessageList";
import { ChainOfThought } from "@/components/chat/ChainOfThought";
import { useChatStore } from "@/stores/chatStore";
import { useConversationInitialization } from "@/features/chat/hooks/useConversationInitialization";

/**
 * ChatPage is the main chat interface component.
 * Orchestrates message list, input, and chain-of-thought visualization.
 */
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
    setConversationId,
    setError,
  } = useChatStore();

  const [inputMessage, setInputMessage] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initialize conversation on mount
  useConversationInitialization({
    onSuccess: (id) => setConversationId(id),
    onError: (err) => setError(err.message),
    enabled: !conversationId,
  });

  const handleSend = async (message: string) => {
    if (!conversationId) return;
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
          <div
            className="rounded-md bg-destructive/10 px-3 py-1 text-sm text-destructive"
            role="alert"
          >
            {error}
          </div>
        )}
      </header>

      {/* Messages area */}
      <div className="relative flex-1 space-y-0 overflow-y-auto px-4 py-12">
        <div className="space-y-12">
          {/* Chain of thought visualization */}
          {orchestratorMessages.length > 0 && (
            <ChainOfThought messages={orchestratorMessages} />
          )}

          {/* Message list */}
          <MessageList
            messages={allMessages}
            isLoading={isLoading && !currentStreamingMessage}
            currentReasoningContent={currentReasoningContent}
            currentReasoningStreaming={currentReasoningStreaming}
          />
        </div>
      </div>

      {/* Input area */}
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-[700px] shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        <ChatInput
          ref={inputRef}
          isLoading={isLoading}
          value={inputMessage}
          onChange={setInputMessage}
          onSubmit={handleSend}
          disabled={isLoading || !conversationId}
        />
      </div>
    </div>
  );
}
```

---

## Phase 3: Create Custom Hooks

### Step 1: `useMessages` Hook

**File**: `src/features/chat/hooks/useMessages.ts`

```typescript
import { useMemo } from "react";
import { useChatStore } from "@/stores/chatStore";
import type { ChatMessage } from "@/types/chat";

/**
 * Hook that combines persisted and streaming messages.
 * Memoized to prevent unnecessary recalculations.
 */
export function useMessages(): ChatMessage[] {
  const {
    messages,
    currentStreamingMessage,
    currentAgentId,
    currentStreamingMessageId,
    currentStreamingTimestamp,
  } = useChatStore();

  return useMemo(
    () => [
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
    ],
    [
      messages,
      currentStreamingMessage,
      currentAgentId,
      currentStreamingMessageId,
      currentStreamingTimestamp,
    ],
  );
}
```

### Step 2: `useSSEStream` Hook

**File**: `src/lib/hooks/useSSEStream.ts`

```typescript
import { useCallback, useRef, useState } from "react";
import { streamChatResponse } from "@/lib/api/chat";
import type {
  SSEDeltaCallback,
  SSECompletedCallback,
  SSEOrchestratorCallback,
  SSEErrorCallback,
} from "@/lib/api/chat";

export interface UseSSEStreamOptions {
  onDelta?: SSEDeltaCallback;
  onAgentComplete?: (agentId: string, content: string) => void;
  onCompleted?: SSECompletedCallback;
  onError?: SSEErrorCallback;
  onReasoningCompleted?: (reasoning: string) => void;
  onOrchestrator?: SSEOrchestratorCallback;
}

/**
 * Custom hook for handling Server-Sent Events streaming.
 * Manages streaming state and error handling.
 */
export function useSSEStream(options: UseSSEStreamOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stream = useCallback(
    async (conversationId: string, message: string) => {
      setIsStreaming(true);
      setError(null);

      try {
        await streamChatResponse(conversationId, message, options);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown streaming error";
        setError(errorMessage);
        options.onError?.(errorMessage);
      } finally {
        setIsStreaming(false);
      }
    },
    [options],
  );

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return {
    stream,
    isStreaming,
    error,
    cancel,
  };
}
```

---

## Phase 4: Testing Examples

### Step 1: Test MessageListItem Component

**File**: `src/components/chat/MessageList/MessageListItem.test.tsx`

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageListItem } from "./MessageListItem";
import type { ChatMessage } from "@/types/chat";

const mockMessage: ChatMessage = {
  id: "1",
  role: "assistant",
  content: "Hello, how can I help you?",
  agentId: "planner",
  createdAt: Date.now(),
};

describe("MessageListItem", () => {
  it("renders message content", () => {
    render(<MessageListItem message={mockMessage} />);

    expect(screen.getByText("Hello, how can I help you?")).toBeInTheDocument();
  });

  it("displays agent ID for assistant messages", () => {
    render(<MessageListItem message={mockMessage} />);

    expect(screen.getByText(/planner/i)).toBeInTheDocument();
  });

  it("shows copy action on last message", () => {
    render(<MessageListItem message={mockMessage} isLastMessage />);

    expect(screen.getByLabelText("Copy")).toBeInTheDocument();
  });

  it("handles copy to clipboard", async () => {
    const user = userEvent.setup();
    const mockClipboard = {
      writeText: vi.fn().mockResolvedValue(undefined),
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(<MessageListItem message={mockMessage} isLastMessage />);

    await user.click(screen.getByLabelText("Copy"));
    expect(mockClipboard.writeText).toHaveBeenCalledWith(mockMessage.content);
  });

  it("displays reasoning content when provided", () => {
    render(
      <MessageListItem
        message={mockMessage}
        reasoningContent="Let me think about this..."
      />
    );

    expect(screen.getByText("Let me think about this...")).toBeInTheDocument();
  });
});
```

### Step 2: Test ChatInput Component

**File**: `src/components/chat/ChatInput/ChatInput.test.tsx`

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "./ChatInput";

describe("ChatInput", () => {
  it("renders input with placeholder", () => {
    const { container } = render(
      <ChatInput value="" onChange={() => {}} onSubmit={() => {}} />
    );

    const textarea = container.querySelector("textarea");
    expect(textarea).toHaveAttribute("placeholder", "Ask anything");
  });

  it("updates value on input change", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<ChatInput value="" onChange={onChange} onSubmit={() => {}} />);

    const textarea = screen.getByPlaceholderText("Ask anything");
    await user.type(textarea, "Hello");

    expect(onChange).toHaveBeenCalledWith("Hello");
  });

  it("submits on button click", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <ChatInput value="Test message" onChange={() => {}} onSubmit={onSubmit} />
    );

    const button = screen.getByLabelText("Send message");
    await user.click(button);

    expect(onSubmit).toHaveBeenCalledWith("Test message");
  });

  it("submits on Ctrl+Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <ChatInput value="Test message" onChange={() => {}} onSubmit={onSubmit} />
    );

    const textarea = screen.getByPlaceholderText("Ask anything");
    await user.type(textarea, "{Control>}{Enter}{/Control}");

    expect(onSubmit).toHaveBeenCalledWith("Test message");
  });

  it("disables button when input is empty", () => {
    render(<ChatInput value="" onChange={() => {}} onSubmit={() => {}} />);

    const button = screen.getByLabelText("Send message");
    expect(button).toBeDisabled();
  });

  it("disables button when loading", () => {
    render(
      <ChatInput
        value="Test"
        onChange={() => {}}
        onSubmit={() => {}}
        isLoading
      />
    );

    const button = screen.getByLabelText("Send message");
    expect(button).toBeDisabled();
  });
});
```

### Step 3: Test Chat Store

**File**: `src/stores/__tests__/chatStore.test.ts`

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatStore } from "../chatStore";

describe("useChatStore", () => {
  beforeEach(() => {
    // Reset store state before each test
    useChatStore.setState({
      messages: [],
      currentStreamingMessage: "",
      isLoading: false,
      error: null,
      conversationId: null,
    });
  });

  it("initializes with default state", () => {
    const { result } = renderHook(() => useChatStore());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("adds a message", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.addMessage({
        role: "user",
        content: "Hello",
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("Hello");
    expect(result.current.messages[0].role).toBe("user");
  });

  it("appends delta to streaming message", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.appendDelta("Hello ");
      result.current.appendDelta("World");
    });

    expect(result.current.currentStreamingMessage).toBe("Hello World");
  });

  it("sets error", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.setError("Test error");
    });

    expect(result.current.error).toBe("Test error");
  });

  it("resets state", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.addMessage({
        role: "user",
        content: "Test",
      });
      result.current.setLoading(true);
      result.current.setError("Error");
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Error");

    act(() => {
      result.current.reset();
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
```

---

## Priority Implementation Order

1. **Week 1**: Hooks extraction (Priority 1.1, 1.2, 1.3)
2. **Week 2**: Component decomposition (Priority 2.1, 2.2)
3. **Week 3**: Testing and refinements
4. **Week 4**: Performance optimization and documentation

---

## Checklist for Each Implementation

- [ ] Create new file following naming conventions
- [ ] Add TypeScript interfaces/types
- [ ] Add JSDoc comments
- [ ] Create corresponding test file
- [ ] Update barrel exports (`index.ts`)
- [ ] Update AGENTS.md documentation
- [ ] Run `npm run lint` and fix any issues
- [ ] Run tests to ensure coverage
- [ ] Create PR with clear description
