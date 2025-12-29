import { useRef, useEffect, useMemo } from "react";
import { useShallow } from "zustand/shallow";
import { PlusIcon, Search, Gauge, Settings, Trash2 } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Button,
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui";
import { useChatStore } from "@/features/chat/stores";
import {
  useInfiniteConversations,
  useCreateConversation,
  useDeleteConversation,
} from "@/api/hooks";
import type { Conversation } from "@/api/types";
import { getGlobalToastInstance } from "@/hooks/use-toast";

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

export const SidebarLeft = ({
  ...props
}: React.ComponentProps<typeof Sidebar>) => {
  const navigate = useNavigate();
  const location = useLocation();

  const { conversationId } = useChatStore(
    useShallow((state) => ({
      conversationId: state.conversationId,
    })),
  );

  // Use React Query for conversations
  const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage } =
    useInfiniteConversations();

  const createConversationMutation = useCreateConversation({
    onSuccess: (newConversation) => {
      // Navigate to the newly created conversation
      navigate(`/chat/${newConversation.conversation_id}`);
    },
  });

  const deleteConversationMutation = useDeleteConversation({
    onSuccess: (_data, deletedId) => {
      const toast = getGlobalToastInstance();
      toast?.toast({
        title: "Conversation Deleted",
        description: "The conversation has been deleted successfully.",
      });
      // If we are currently viewing this conversation, navigate home
      if (location.pathname === `/chat/${deletedId}`) {
        navigate("/");
      }
    },
    onError: (error) => {
      const toast = getGlobalToastInstance();
      toast?.toast({
        title: "Failed to Delete Conversation",
        description:
          error.message || "An error occurred while deleting the conversation.",
        variant: "destructive",
      });
    },
  });

  // Flatten all pages into a single array
  const conversations = useMemo(() => {
    if (!data) return [];
    // Infinite query data has a .pages property which is an array of arrays
    const allConversations = data.pages.flat();
    return [...allConversations].sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
  }, [data]);

  const handleCreateConversation = () => {
    createConversationMutation.mutate("New Chat");
  };

  const handleDeleteConversation = (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent selecting the conversation when clicking delete
    const confirmed = window.confirm(
      "Are you sure you want to delete this conversation? This action cannot be undone.",
    );
    if (confirmed) {
      deleteConversationMutation.mutate(id);
    }
  };

  const observerInstanceRef = useRef<IntersectionObserver | null>(null);
  const hasMoreRef = useRef(hasNextPage);
  const isLoadingRef = useRef(isFetchingNextPage);
  const loadMoreRef = useRef(fetchNextPage);

  // Keep refs in sync with latest values
  useEffect(() => {
    hasMoreRef.current = hasNextPage ?? false;
    isLoadingRef.current = isFetchingNextPage;
    loadMoreRef.current = fetchNextPage;
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const setObserverRef = (el: HTMLDivElement | null) => {
    // Clean up existing observer if element changes
    if (observerInstanceRef.current) {
      observerInstanceRef.current.disconnect();
      observerInstanceRef.current = null;
    }

    // Create and observe when element exists
    if (el) {
      const observer = new IntersectionObserver(
        (entries) => {
          if (
            entries[0].isIntersecting &&
            hasMoreRef.current &&
            !isLoadingRef.current
          ) {
            void loadMoreRef.current();
          }
        },
        { threshold: 0.1 },
      );

      observer.observe(el);
      observerInstanceRef.current = observer;
    }
  };

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (observerInstanceRef.current) {
        observerInstanceRef.current.disconnect();
        observerInstanceRef.current = null;
      }
    };
  }, []);

  const grouped = useMemo(
    () => groupConversations(conversations),
    [conversations],
  );

  return (
    <Sidebar collapsible="offcanvas" variant="floating" {...props}>
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 px-4 py-4">
        <div className="flex flex-row items-center gap-2 min-w-0 flex-1">
          <div className="bg-secondary/80 flex size-6 items-center justify-center rounded-md">
            <img
              src="/logo_darkmode.svg"
              alt="AgenticFleet"
              className="size-4 shrink-0"
            />
          </div>
          <div className="text-sm font-semibold tracking-tight text-foreground truncate">
            AgenticFleet
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-md"
            aria-label="Search"
          >
            <Search className="size-3.5" />
          </Button>
        </div>
      </SidebarHeader>

      {/* Actions Group */}
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={handleCreateConversation}
                disabled={createConversationMutation.isPending}
                tooltip="Start new chat"
                className="bg-secondary/80 text-foreground hover:bg-secondary font-medium"
              >
                <PlusIcon className="size-4" />
                <span>New Chat</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                isActive={location.pathname === "/dashboard"}
                onClick={() => navigate("/dashboard")}
                tooltip="Optimization Dashboard"
              >
                <Gauge className="size-4" />
                <span>Optimization</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <SidebarContent className="scrollbar-none">
        {/* Conversations */}
        {conversations.length === 0 && isFetching ? (
          <div className="px-4 py-2 text-sm text-muted-foreground">
            Loading…
          </div>
        ) : grouped.length === 0 ? (
          <div className="px-4 py-2 text-sm text-muted-foreground text-center animate-in fade-in duration-500">
            No conversations yet.
          </div>
        ) : (
          <>
            {grouped.map((group) => (
              <SidebarGroup key={group.period}>
                <SidebarGroupLabel>{group.period}</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {group.conversations.map((conversation) => (
                      <SidebarMenuItem key={conversation.conversation_id}>
                        <SidebarMenuButton
                          isActive={
                            conversation.conversation_id === conversationId
                          }
                          onClick={() =>
                            navigate(`/chat/${conversation.conversation_id}`)
                          }
                        >
                          <span className="truncate">
                            {getConversationTitle(conversation)}
                          </span>
                        </SidebarMenuButton>
                        <SidebarMenuAction
                          onClick={(e) =>
                            handleDeleteConversation(
                              e,
                              conversation.conversation_id,
                            )
                          }
                          disabled={deleteConversationMutation.isPending}
                          showOnHover
                        >
                          <Trash2 className="size-3.5" />
                          <span className="sr-only">Delete conversation</span>
                        </SidebarMenuAction>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            ))}
            <div
              ref={setObserverRef}
              className="h-2 w-full"
              aria-hidden="true"
            />
            {isFetchingNextPage && (
              <div className="px-4 py-2 text-xs text-muted-foreground animate-pulse">
                Loading more...
              </div>
            )}
          </>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-border p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Settings">
              <Settings className="size-4" />
              <span>Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
};
