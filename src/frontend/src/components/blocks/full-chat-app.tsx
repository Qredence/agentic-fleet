import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/prompt-kit/message";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/prompt-kit/chain-of-thought";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/prompt-kit/reasoning";
import { TextShimmer } from "@/components/prompt-kit/text-shimmer";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import type { Conversation, Message as ChatMessage } from "@/api/types";
import type { ConversationStep } from "@/api/types";
import { useChatStore } from "@/stores";
import { cn } from "@/lib/utils";
import { Copy, PlusIcon, Search, Square, ArrowUp } from "lucide-react";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/shallow";

function formatStepTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function getStepLabel(step: ConversationStep): { label: string } {
  const type = step.type;
  if (type === "error") return { label: "Error" };
  if (type === "analysis") return { label: "Analysis" };
  if (type === "routing") return { label: "Routing" };
  if (type === "quality") return { label: "Quality" };
  if (type === "progress") return { label: "Progress" };
  if (type === "request") return { label: "Request" };
  if (type === "tool_call") return { label: "Tool" };
  if (type === "handoff") return { label: "Handoff" };
  if (type === "agent_start") return { label: "Agent started" };
  if (type === "agent_complete") return { label: "Agent complete" };
  if (type === "agent_output") return { label: "Output" };
  if (type === "agent_thought") return { label: "Thought" };
  if (type === "reasoning") return { label: "Reasoning" };
  if (type === "status") return { label: "Status" };
  return { label: "Event" };
}

function splitSteps(steps: ConversationStep[]): {
  reasoning: string;
  trace: ConversationStep[];
} {
  let reasoning = "";
  const trace: ConversationStep[] = [];

  for (const step of steps) {
    if (step.type === "reasoning") {
      reasoning += step.content;
    } else {
      trace.push(step);
    }
  }

  return { reasoning, trace };
}

function coerceString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function looksJson(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}

function parseResponse(value: string): unknown {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (!looksJson(trimmed)) return trimmed;
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

function WorkflowRequestResponder({
  requestId,
  requestType,
}: {
  requestId: string;
  requestType?: string;
}) {
  const { sendWorkflowResponse, isLoading } = useChatStore(
    useShallow((state) => ({
      sendWorkflowResponse: state.sendWorkflowResponse,
      isLoading: state.isLoading,
    })),
  );

  const [value, setValue] = useState("");

  const loweredType = (requestType || "").toLowerCase();
  const isApproval = loweredType.includes("approval");

  const submit = (payload: unknown) => {
    sendWorkflowResponse(requestId, payload);
  };

  return (
    <div className="mt-2 rounded-md border border-border bg-muted/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {requestType
            ? `Type: ${requestType}`
            : "Workflow is waiting for a response"}
        </div>
        <div className="text-xs text-muted-foreground">
          request_id: {requestId}
        </div>
      </div>

      {isApproval ? (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => submit({ approved: true })}
            disabled={!isLoading}
          >
            Approve
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => submit({ approved: false })}
            disabled={!isLoading}
          >
            Deny
          </Button>
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={
            isApproval
              ? 'Optional: provide JSON payload (e.g. {"approved": true}) or a note'
              : "Enter a response (plain text or JSON)"
          }
          className="min-h-20"
        />
        <div className="flex items-center justify-end">
          <Button
            size="sm"
            onClick={() => submit(parseResponse(value))}
            disabled={!isLoading || !value.trim()}
          >
            Send response
          </Button>
        </div>
      </div>
    </div>
  );
}

function AssistantTrace({
  message,
  isStreaming,
}: {
  message: ChatMessage;
  isStreaming: boolean;
}) {
  const steps = message.steps ?? [];
  const phase = message.workflowPhase?.trim();

  if (steps.length === 0 && !phase) return null;

  const { reasoning, trace } = splitSteps(steps);

  return (
    <div className="w-full space-y-3">
      {phase && isStreaming && !message.content ? (
        <div className="text-sm text-muted-foreground">
          <TextShimmer as="span">{phase}</TextShimmer>
        </div>
      ) : null}

      {reasoning.trim() ? (
        <Reasoning isStreaming={isStreaming} className="w-full">
          <ReasoningTrigger className="text-xs">Reasoning</ReasoningTrigger>
          <ReasoningContent
            className="mt-2"
            contentClassName="whitespace-pre-wrap wrap-break-word"
          >
            {reasoning}
          </ReasoningContent>
        </Reasoning>
      ) : null}

      {trace.length ? (
        <div className="rounded-lg border border-border bg-card/40 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            {isStreaming ? (
              <TextShimmer as="span" className="text-sm">
                Events
              </TextShimmer>
            ) : (
              <span className="text-sm text-muted-foreground">Events</span>
            )}
            <span className="text-xs text-muted-foreground">
              {trace.length}
            </span>
          </div>

          <ChainOfThought className="mt-2">
            {trace.map((step) => {
              const { label } = getStepLabel(step);
              const time = formatStepTime(step.timestamp);
              const agent =
                (step.data?.author as string | undefined) ??
                (step.data?.agent_id as string | undefined);
              const output =
                typeof step.data?.output === "string"
                  ? step.data.output
                  : undefined;
              const requestId =
                coerceString(step.data?.request_id) ||
                // fallback: some payloads may use camelCase
                coerceString(
                  (step.data as Record<string, unknown> | undefined)?.requestId,
                );
              const requestType = coerceString(step.data?.request_type);

              const triggerParts = [
                agent ? `${label}: ${agent}` : label,
                step.kind,
                time,
              ].filter(Boolean);

              const extraData = step.data ? { ...step.data } : undefined;
              if (extraData && "output" in extraData) {
                delete (extraData as Record<string, unknown>).output;
              }
              const hasExtraData =
                !!extraData && Object.keys(extraData).length > 0;

              return (
                <ChainOfThoughtStep key={step.id} defaultOpen={false}>
                  <ChainOfThoughtTrigger
                    className={cn(
                      step.type === "error" &&
                        "text-destructive hover:text-destructive",
                    )}
                  >
                    {triggerParts.join(" · ")}
                  </ChainOfThoughtTrigger>

                  <ChainOfThoughtContent>
                    <ChainOfThoughtItem className="whitespace-pre-wrap wrap-break-word">
                      {step.content}
                    </ChainOfThoughtItem>

                    {step.type === "request" && requestId ? (
                      <ChainOfThoughtItem>
                        <WorkflowRequestResponder
                          requestId={requestId}
                          requestType={requestType}
                        />
                      </ChainOfThoughtItem>
                    ) : null}

                    {output ? (
                      <ChainOfThoughtItem className="whitespace-pre-wrap wrap-break-word text-foreground">
                        {output}
                      </ChainOfThoughtItem>
                    ) : null}

                    {hasExtraData ? (
                      <ChainOfThoughtItem>
                        <details>
                          <summary className="cursor-pointer select-none text-xs text-muted-foreground">
                            Details
                          </summary>
                          <pre className="mt-2 overflow-x-auto rounded-md bg-muted/40 p-2 text-xs text-foreground">
                            {JSON.stringify(extraData, null, 2)}
                          </pre>
                        </details>
                      </ChainOfThoughtItem>
                    ) : null}
                  </ChainOfThoughtContent>
                </ChainOfThoughtStep>
              );
            })}
          </ChainOfThought>
        </div>
      ) : null}
    </div>
  );
}

type ConversationGroup = {
  period: string;
  conversations: Conversation[];
};

function groupConversations(
  conversations: Conversation[],
): ConversationGroup[] {
  const now = new Date();
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);

  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);

  const startOfLast7Days = new Date(startOfToday);
  startOfLast7Days.setDate(startOfLast7Days.getDate() - 7);

  const startOfLast30Days = new Date(startOfToday);
  startOfLast30Days.setDate(startOfLast30Days.getDate() - 30);

  const groups: Record<string, Conversation[]> = {
    Today: [],
    Yesterday: [],
    "Last 7 days": [],
    "Last 30 days": [],
    Older: [],
  };

  for (const conv of conversations) {
    const updatedAt = new Date(conv.updated_at);
    if (updatedAt >= startOfToday) {
      groups.Today.push(conv);
    } else if (updatedAt >= startOfYesterday) {
      groups.Yesterday.push(conv);
    } else if (updatedAt >= startOfLast7Days) {
      groups["Last 7 days"].push(conv);
    } else if (updatedAt >= startOfLast30Days) {
      groups["Last 30 days"].push(conv);
    } else {
      groups.Older.push(conv);
    }
  }

  return (Object.keys(groups) as Array<keyof typeof groups>)
    .map((period) => ({ period, conversations: groups[period] }))
    .filter((g) => g.conversations.length > 0);
}

function getConversationTitle(conversation: Conversation | undefined): string {
  if (!conversation) return "New Chat";
  return conversation.title?.trim() ? conversation.title : "New Chat";
}

function ChatSidebar() {
  const {
    conversations,
    conversationId,
    createConversation,
    selectConversation,
    isConversationsLoading,
  } = useChatStore(
    useShallow((state) => ({
      conversations: state.conversations,
      conversationId: state.conversationId,
      createConversation: state.createConversation,
      selectConversation: state.selectConversation,
      isConversationsLoading: state.isConversationsLoading,
    })),
  );

  const grouped = useMemo(
    () => groupConversations(conversations),
    [conversations],
  );

  return (
    <Sidebar>
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 px-2 py-4">
        <div className="flex flex-row items-center gap-2 px-2">
          <div className="bg-primary/10 size-8 rounded-md" />
          <div className="text-md font-base text-primary tracking-tight">
            AgenticFleet
          </div>
        </div>
        <Button variant="ghost" className="size-8" aria-label="Search">
          <Search className="size-4" />
        </Button>
      </SidebarHeader>

      <SidebarContent className="pt-4">
        <div className="px-4">
          <Button
            variant="outline"
            className="mb-4 flex w-full items-center gap-2"
            onClick={() => void createConversation()}
            disabled={isConversationsLoading}
            aria-label="Start new chat"
          >
            <PlusIcon className="size-4" />
            <span>New Chat</span>
          </Button>
        </div>

        {isConversationsLoading ? (
          <div className="px-4 py-2 text-sm text-muted-foreground">
            Loading…
          </div>
        ) : grouped.length === 0 ? (
          <div className="px-4 py-2 text-sm text-muted-foreground">
            No conversations yet.
          </div>
        ) : (
          grouped.map((group) => (
            <SidebarGroup key={group.period}>
              <SidebarGroupLabel>{group.period}</SidebarGroupLabel>
              <SidebarMenu>
                {group.conversations.map((conversation) => (
                  <SidebarMenuButton
                    key={conversation.id}
                    isActive={conversation.id === conversationId}
                    onClick={() => void selectConversation(conversation.id)}
                  >
                    <span>{getConversationTitle(conversation)}</span>
                  </SidebarMenuButton>
                ))}
              </SidebarMenu>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>
    </Sidebar>
  );
}

function ChatMessages({
  messages,
  isLoading,
}: {
  messages: ChatMessage[];
  isLoading: boolean;
}) {
  return (
    <ChatContainerRoot className="h-full">
      <ChatContainerContent className="px-5 py-12">
        <div className="flex flex-col gap-8">
          {messages.map((message, index) => {
            const isAssistant = message.role === "assistant";
            const isLastMessage = index === messages.length - 1;
            const isStreaming = isAssistant && isLastMessage && isLoading;

            if (!isAssistant) {
              return (
                <Message
                  key={message.id || `${message.role}-${index}`}
                  className="mx-auto w-full max-w-3xl justify-end px-6"
                >
                  <MessageContent className="bg-muted text-foreground max-w-[85%] rounded-3xl px-5 py-2.5 sm:max-w-[75%] whitespace-pre-wrap break-normal">
                    {message.content}
                  </MessageContent>
                </Message>
              );
            }

            return (
              <Message
                key={message.id || `${message.role}-${index}`}
                className="mx-auto w-full max-w-3xl flex-col gap-2 px-6 items-start"
              >
                <AssistantTrace message={message} isStreaming={isStreaming} />

                <div className="group flex w-full flex-col gap-0">
                  <MessageContent
                    className={cn(
                      "text-foreground prose flex-1 rounded-lg bg-transparent p-0",
                      isStreaming && "whitespace-pre-wrap",
                    )}
                    markdown={!isStreaming}
                  >
                    {isStreaming ? (
                      <>
                        {message.content}
                        <span className="ml-0.5 inline-block w-2 animate-pulse align-baseline">
                          ▍
                        </span>
                      </>
                    ) : (
                      message.content
                    )}
                  </MessageContent>

                  {!isStreaming && (
                    <MessageActions className="-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                      <MessageAction tooltip="Copy" delayDuration={100}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-full"
                          onClick={() =>
                            void navigator.clipboard.writeText(message.content)
                          }
                          aria-label="Copy response"
                        >
                          <Copy className="size-4" />
                        </Button>
                      </MessageAction>
                    </MessageActions>
                  )}
                </div>
              </Message>
            );
          })}
        </div>
      </ChatContainerContent>

      <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
        <ScrollButton className="shadow-sm" />
      </div>
    </ChatContainerRoot>
  );
}

function ChatContent() {
  const {
    messages,
    isLoading,
    conversationId,
    conversations,
    sendMessage,
    cancelStreaming,
  } = useChatStore(
    useShallow((state) => ({
      messages: state.messages,
      isLoading: state.isLoading,
      conversationId: state.conversationId,
      conversations: state.conversations,
      sendMessage: state.sendMessage,
      cancelStreaming: state.cancelStreaming,
    })),
  );

  const [prompt, setPrompt] = useState("");

  const currentConversation = useMemo(
    () => conversations.find((c) => c.id === conversationId),
    [conversations, conversationId],
  );

  const headerTitle = getConversationTitle(currentConversation);

  const handleSubmit = () => {
    const text = prompt.trim();
    if (!text || isLoading) return;
    setPrompt("");
    void sendMessage(text);
  };

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      <header className="bg-background z-10 flex h-16 w-full shrink-0 items-center gap-2 border-b px-4">
        <SidebarTrigger className="-ml-1" />
        <div className="text-foreground truncate">{headerTitle}</div>
      </header>

      <div className="relative flex-1 overflow-y-auto">
        <ChatMessages messages={messages} isLoading={isLoading} />
      </div>

      <div className="bg-background z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        <div className="mx-auto max-w-3xl">
          <PromptInput
            isLoading={isLoading}
            value={prompt}
            onValueChange={setPrompt}
            onSubmit={handleSubmit}
            className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
          >
            <div className="flex flex-col">
              <PromptInputTextarea
                placeholder="Ask anything..."
                className="min-h-11 pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
              />

              <PromptInputActions className="mt-5 flex w-full items-center justify-end gap-2 px-3 pb-3">
                {isLoading ? (
                  <PromptInputAction tooltip="Stop">
                    <Button
                      variant="outline"
                      size="icon"
                      className="size-9 rounded-full"
                      onClick={cancelStreaming}
                      aria-label="Stop streaming"
                    >
                      <Square className="size-4 fill-current" />
                    </Button>
                  </PromptInputAction>
                ) : (
                  <Button
                    size="icon"
                    disabled={!prompt.trim() || isLoading}
                    onClick={handleSubmit}
                    className="size-9 rounded-full"
                    aria-label="Send message"
                  >
                    <ArrowUp size={18} />
                  </Button>
                )}
              </PromptInputActions>
            </div>
          </PromptInput>
        </div>
      </div>
    </main>
  );
}

export function FullChatApp() {
  return (
    <SidebarProvider>
      <ChatSidebar />
      <SidebarInset>
        <ChatContent />
      </SidebarInset>
    </SidebarProvider>
  );
}
