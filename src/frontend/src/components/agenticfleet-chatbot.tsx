/**
 * AgenticFleet Chatbot Component
 *
 * Adapted from prompt-kit chatbot to work with FastAPI HaxUI backend.
 * Uses custom useFastAPIChat hook instead of Vercel AI SDK.
 */

import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import { Loader } from "@/components/prompt-kit/loader";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/prompt-kit/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { Tool } from "@/components/prompt-kit/tool";
import { Button } from "@/components/ui/button";
import type {
  ApprovalActionState,
  Message as ChatMessage,
  PendingApproval,
} from "@/lib/use-fastapi-chat";
import { useFastAPIChat } from "@/lib/use-fastapi-chat";
import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowUp, Check, Clock, Loader2, X } from "lucide-react";
import { memo, useCallback, useMemo } from "react";
import MessageList from "./message-list";
import PendingApprovals from "./pending-approvals";
import WelcomeMessage from "./welcome-message";

type MessageComponentProps = {
  message: ChatMessage;
};

export const MessageComponent = memo(({ message }: MessageComponentProps) => {
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";
  const isUser = message.role === "user";
  const actorLabel =
    message.actor ?? (isAssistant ? "Assistant" : isUser ? "You" : "Workflow");

  return (
    <Message
      className={cn(
        "mx-auto flex w-full max-w-3xl flex-col gap-2 px-0 md:px-6",
        isUser ? "items-end" : "items-start"
      )}
    >
      <div
        className={cn(
          "flex w-full items-end gap-3",
          isUser ? "flex-row-reverse" : "flex-row"
        )}
      >
        {isAssistant ? (
          <MessageAvatar
            className="mb-0.5 h-6 w-6"
            src="https://prompt-kit.com/logo.png"
            alt="AgenticFleet Assistant"
            fallback="AF"
          />
        ) : isSystem ? (
          <MessageAvatar
            className="mb-0.5 h-6 w-6 bg-muted"
            alt={actorLabel}
            fallback={actorLabel.slice(0, 2).toUpperCase()}
          />
        ) : (
          <MessageAvatar
            className="h-6 w-6"
            src="https://github.com/github.png"
            alt="User"
            fallback="U"
          />
        )}
        {isAssistant ? (
          <MessageContent
            className="prose text-primary w-full max-w-[85%] flex-1 overflow-x-auto rounded-lg bg-transparent p-0 py-0 sm:max-w-[75%]"
            markdown
          >
            {message.content}
          </MessageContent>
        ) : isSystem ? (
          <MessageContent className="bg-muted text-muted-foreground max-w-[85%] rounded-xl px-4 py-3 text-sm sm:max-w-[75%]">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/80">
              {actorLabel}
            </div>
            <div className="whitespace-pre-wrap">{message.content}</div>
          </MessageContent>
        ) : (
          <MessageContent className="bg-secondary text-primary max-w-[85%] sm:max-w-[75%]">
            {message.content}
          </MessageContent>
        )}
      </div>
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className={cn("w-full sm:max-w-[75%]", isUser ? "mr-9" : "ml-9")}>
          {message.toolCalls.map((toolCall) => (
            <Tool
              key={toolCall.id}
              toolPart={{
                type: toolCall.name,
                state: toolCall.state,
                input: toolCall.input,
                output: toolCall.output,
                toolCallId: toolCall.id,
                errorText: toolCall.errorText,
              }}
              defaultOpen={false}
            />
          ))}
        </div>
      )}
    </Message>
  );
});

MessageComponent.displayName = "MessageComponent";

type PendingApprovalCardProps = {
  approval: PendingApproval;
  status?: ApprovalActionState;
  onApprove: () => void;
  onReject: () => void;
};

const PendingApprovalCard = memo(
  ({ approval, status, onApprove, onReject }: PendingApprovalCardProps) => {
    const isSubmitting = status?.status === "submitting";
    const errorMessage = status?.status === "error" ? status.error : null;
    const formattedArguments = useMemo(() => {
      if (
        approval.functionCall.arguments &&
        Object.keys(approval.functionCall.arguments).length > 0
      ) {
        return JSON.stringify(approval.functionCall.arguments, null, 2);
      }
      return "No additional details provided.";
    }, [approval.functionCall.arguments]);

    return (
      <div className="border border-yellow-200/60 bg-yellow-100/30 text-yellow-900 rounded-2xl p-4 shadow-sm backdrop-blur-sm">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-yellow-600" aria-hidden="true" />
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wide">
                Approval Required
              </span>
              <span className="text-sm text-muted-foreground">
                {approval.functionCall.name}
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground/80">
            #{approval.requestId.slice(-6)}
          </span>
        </div>

        <div className="mt-3 rounded-lg bg-background/80 p-3 text-left text-xs leading-relaxed text-muted-foreground">
          <pre className="whitespace-pre-wrap break-words">
            {formattedArguments}
          </pre>
        </div>

        {errorMessage && (
          <div className="mt-3 flex items-center gap-2 text-xs text-destructive">
            <AlertTriangle size={14} aria-hidden="true" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            className="gap-2"
            disabled={isSubmitting}
            onClick={onApprove}
          >
            {isSubmitting ? (
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Check size={16} aria-hidden="true" />
            )}
            Approve
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="gap-2"
            disabled={isSubmitting}
            onClick={onReject}
          >
            {isSubmitting ? (
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <X size={16} aria-hidden="true" />
            )}
            Reject
          </Button>
        </div>
      </div>
    );
  }
);

PendingApprovalCard.displayName = "PendingApprovalCard";

const LoadingMessage = memo(() => (
  <Message className="mx-auto flex w-full max-w-3xl flex-col items-start gap-2 px-0 md:px-6">
    <div className="flex w-full items-end gap-3">
      <MessageAvatar
        className="mb-0.5 h-6 w-6"
        src="https://prompt-kit.com/logo.png"
        alt="AgenticFleet Assistant"
        fallback="AF"
      />
      <div className="text-foreground prose w-full max-w-[85%] flex-1 overflow-x-auto rounded-lg bg-transparent p-0 py-0 sm:max-w-[75%]">
        <Loader size="md" text="Thinking..." />
      </div>
    </div>
  </Message>
));

LoadingMessage.displayName = "LoadingMessage";

const ErrorMessage = memo(({ error }: { error: Error }) => (
  <Message className="not-prose mx-auto flex w-full max-w-3xl flex-col items-start gap-2 px-0 md:px-6">
    <div className="flex w-full items-end gap-3">
      <MessageAvatar
        className="mb-0.5 h-6 w-6"
        src="https://prompt-kit.com/logo.png"
        alt="AgenticFleet Assistant"
        fallback="AF"
      />
      <div className="text-primary flex min-w-0 flex-1 flex-row items-center gap-2 rounded-lg border-2 border-red-300 bg-red-300/20 px-2 py-1">
        <AlertTriangle size={16} className="text-red-500" />
        <p className="text-red-500">{error.message}</p>
      </div>
    </div>
  </Message>
));

ErrorMessage.displayName = "ErrorMessage";

// Export components for use in other files
export { ErrorMessage, LoadingMessage, PendingApprovalCard };
export type { PendingApprovalCardProps };

export interface AgenticFleetChatbotProps {
  /** Model/entity ID to use (default: 'magentic_fleet') */
  model?: string;
  /** Conversation ID for context */
  conversationId?: string;
  /** Custom placeholder text */
  placeholder?: string;
}

export default function AgenticFleetChatbot({
  model = "magentic_fleet",
  conversationId,
  placeholder = "Ask AgenticFleet anything...",
}: AgenticFleetChatbotProps) {
  const {
    messages,
    input,
    setInput,
    status,
    error,
    sendMessage,
    pendingApprovals,
    approvalStatuses,
    respondToApproval,
    conversationId: activeConversationId,
  } = useFastAPIChat({
    model,
    conversationId,
  });

  const trimmedInput = input.trim();
  const isLoading = useMemo(
    () => status === "submitted" || status === "streaming",
    [status]
  );

  const handleSubmit = useCallback(() => {
    if (!trimmedInput) return;
    void sendMessage(trimmedInput);
    setInput("");
  }, [sendMessage, setInput, trimmedInput]);

  const makeApprovalHandler = useCallback(
    (requestId: string, approved: boolean) => () =>
      respondToApproval(requestId, approved).catch(() => undefined),
    [respondToApproval]
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <ChatContainerRoot className="relative flex-1 overflow-y-auto px-1 py-12 md:px-4">
        <ChatContainerContent className="space-y-12 px-1 py-12 md:px-4">
          {messages.length === 0 && <WelcomeMessage />}

          {pendingApprovals.length > 0 && (
            <PendingApprovals
              pendingApprovals={pendingApprovals}
              approvalStatuses={approvalStatuses}
              onRespondToApproval={makeApprovalHandler}
            />
          )}

          <MessageList
            messages={messages}
            isLoading={isLoading}
            error={error}
          />
        </ChatContainerContent>
      </ChatContainerRoot>
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        <PromptInput
          isLoading={isLoading}
          value={input}
          onValueChange={setInput}
          onSubmit={handleSubmit}
          className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
        >
          <div className="flex flex-col">
            <PromptInputTextarea
              placeholder={placeholder}
              className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
            />

            <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 p-2">
              <div className="text-xs text-muted-foreground space-y-0.5">
                <div>{isLoading ? "Generating..." : `Model: ${model}`}</div>
                {activeConversationId ? (
                  <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground/80">
                    {activeConversationId}
                  </div>
                ) : (
                  <div className="text-muted-foreground/70">
                    New conversation
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="icon"
                  type="button"
                  aria-label={isLoading ? "Generating response" : "Send"}
                  disabled={!trimmedInput || isLoading}
                  onClick={handleSubmit}
                  className="size-9 rounded-full"
                >
                  {status === "ready" || status === "error" ? (
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
