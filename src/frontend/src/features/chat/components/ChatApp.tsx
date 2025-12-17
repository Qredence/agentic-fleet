import { ChainOfThoughtTrace } from "./chain-of-thought";
import { ChatHeader } from "./chat-header";
import { ChatMessages } from "./chat-messages";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "./prompt-input";
import {
  Button,
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
} from "@/shared/components/ui";
import type { Conversation, Message as ChatMessage } from "@/api/types";
import { useChatStore } from "../stores";
import { OptimizationDashboard } from "@/features/dashboard";
import { PlusIcon, Search, Square, ArrowUp, Gauge } from "lucide-react";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/shallow";

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
    activeView,
    setActiveView,
  } = useChatStore(
    useShallow((state) => ({
      conversations: state.conversations,
      conversationId: state.conversationId,
      createConversation: state.createConversation,
      selectConversation: state.selectConversation,
      isConversationsLoading: state.isConversationsLoading,
      activeView: state.activeView,
      setActiveView: state.setActiveView,
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
          <img
            src="/logo_darkmode.svg"
            alt="AgenticFleet"
            className="size-5 rounded-md"
          />
          <div className="text-md font-base tracking-tight text-foreground">
            AgenticFleet
          </div>
        </div>
        <Button variant="ghost" className="size-8" aria-label="Search">
          <Search className="size-4" />
        </Button>
      </SidebarHeader>

      <SidebarContent className="pt-4">
        <div className="flex flex-wrap px-4">
          <Button
            variant="outline"
            className="mb-4 flex w-fit flex-wrap items-start justify-start gap-2 rounded-3xl border-0 text-left"
            onClick={() => void createConversation()}
            disabled={isConversationsLoading}
            aria-label="Start new chat"
          >
            <PlusIcon className="size-4" />
            <span>New Chat</span>
          </Button>
        </div>

        <SidebarGroup>
          <SidebarGroupLabel>Tools</SidebarGroupLabel>
          <SidebarMenu>
            <SidebarMenuButton
              isActive={activeView === "dashboard"}
              onClick={() => setActiveView("dashboard")}
              aria-label="Open optimization dashboard"
            >
              <Gauge className="mr-2 size-4" />
              <span>Optimization</span>
            </SidebarMenuButton>
          </SidebarMenu>
        </SidebarGroup>

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

function ChatContent() {
  const {
    messages,
    isLoading,
    conversationId,
    conversations,
    sendMessage,
    cancelStreaming,
    sendWorkflowResponse,
  } = useChatStore(
    useShallow((state) => ({
      messages: state.messages,
      isLoading: state.isLoading,
      conversationId: state.conversationId,
      conversations: state.conversations,
      sendMessage: state.sendMessage,
      cancelStreaming: state.cancelStreaming,
      sendWorkflowResponse: state.sendWorkflowResponse,
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
      <ChatHeader
        title={headerTitle}
        sidebarTrigger={<SidebarTrigger className="-ml-1" />}
      />

      <div className="relative flex-1 overflow-y-auto">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          renderTrace={(message: ChatMessage, isStreaming: boolean) => (
            <ChainOfThoughtTrace
              message={message}
              isStreaming={isStreaming}
              isLoading={isLoading}
              onWorkflowResponse={(requestId, payload) =>
                sendWorkflowResponse(requestId, payload)
              }
            />
          )}
        />
      </div>

      <div className="z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5">
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

export function ChatApp() {
  const activeView = useChatStore((state) => state.activeView);
  return (
    <SidebarProvider>
      <ChatSidebar />
      <SidebarInset>
        {activeView === "dashboard" ? (
          <OptimizationDashboard />
        ) : (
          <ChatContent />
        )}
      </SidebarInset>
    </SidebarProvider>
  );
}
