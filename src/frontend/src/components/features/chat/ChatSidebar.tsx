import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Edit, MessageSquare, MoreVertical, Plus, Settings, Trash2 } from "lucide-react";
import { useMemo } from "react";

import { Button } from "@/components/ui/shadcn/button";
import { DropdownMenu } from "@/components/ui/shadcn/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { API_ENDPOINTS, buildApiUrl } from "@/lib/api-config";
import { cn } from "@/lib/utils";

interface ChatSidebarProps {
  selectedConversationId?: string;
  onSelectConversation?: (conversationId?: string) => void;
}

interface ConversationSummary {
  id: string;
  created_at?: number;
  metadata?: Record<string, string> | null;
}

const mapConversations = (items: ConversationSummary[]) =>
  items.map((item) => {
    const createdAt = item.created_at ? new Date(item.created_at * 1000) : undefined;
    const metadata = item.metadata || {};
    const title =
      metadata.title || metadata.workflow || `Conversation ${item.id.slice(-6).toUpperCase()}`;
    return {
      id: item.id,
      title,
      timestamp: createdAt ? createdAt.toLocaleString() : "",
    };
  });

export const ChatSidebar = ({ selectedConversationId, onSelectConversation }: ChatSidebarProps) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.CONVERSATIONS));
      if (!response.ok) {
        throw new Error(`Failed to load conversations: ${response.status}`);
      }
      const payload = await response.json();
      return Array.isArray(payload?.data) ? payload.data : [];
    },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    retry: false,
  });

  const conversations = useMemo(() => mapConversations(data || []), [data]);

  const { mutateAsync: createConversation, isPending: isCreating } = useMutation({
    mutationFn: async () => {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.CONVERSATIONS), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Failed to create conversation: ${response.status}`);
      }
      return response.json();
    },
    onSuccess: (summary: ConversationSummary) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      onSelectConversation?.(summary.id);
    },
    onError: (error) => {
      toast({
        title: "Unable to create conversation",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    },
  });

  const handleNewChat = async () => {
    const summary = await createConversation();
    if (!summary?.id) {
      toast({
        title: "Conversation not created",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-6 border-b border-border/50">
        <Button
          onClick={handleNewChat}
          variant="ghost"
          className="w-full justify-start gap-2 hover:bg-muted/50 transition-smooth"
          disabled={isCreating}
        >
          {isCreating ? (
            <MessageSquare className="h-4 w-4 animate-pulse" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          <span className="font-medium">New Chat</span>
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MessageSquare className="h-4 w-4 animate-pulse" /> Loading conversations...
          </div>
        )}

        {isError && (
          <div className="text-xs text-destructive bg-destructive/10 rounded-md p-3">
            Failed to load conversations
          </div>
        )}

        {!isLoading && conversations.length === 0 && (
          <div className="text-xs text-muted-foreground">
            No conversations yet. Start a new chat!
          </div>
        )}

        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            onClick={() => onSelectConversation?.(conversation.id)}
            className={cn(
              "w-full text-left p-3 rounded-lg transition-smooth group",
              selectedConversationId === conversation.id ? "bg-muted" : "hover:bg-muted/50"
            )}
          >
            <div className="flex items-start gap-3">
              <MessageSquare className="h-4 w-4 mt-1 text-muted-foreground group-hover:text-foreground transition-smooth" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-foreground">{conversation.title}</p>
                {conversation.timestamp && (
                  <p className="text-xs text-muted-foreground mt-1">{conversation.timestamp}</p>
                )}
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <DropdownMenu
                  options={[
                    {
                      label: "Edit",
                      onClick: () => {
                        toast({
                          title: "Edit conversation",
                          description: `Editing ${conversation.title}`,
                        });
                      },
                      Icon: <Edit className="h-4 w-4" />,
                    },
                    {
                      label: "Archive",
                      onClick: () => {
                        toast({
                          title: "Archive conversation",
                          description: `Archived ${conversation.title}`,
                        });
                      },
                      Icon: <Archive className="h-4 w-4" />,
                    },
                    {
                      label: "Delete",
                      onClick: () => {
                        toast({
                          title: "Delete conversation",
                          description: `Deleted ${conversation.title}`,
                          variant: "destructive",
                        });
                      },
                      Icon: <Trash2 className="h-4 w-4" />,
                    },
                  ]}
                >
                  <MoreVertical className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                </DropdownMenu>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-border/50">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 hover:bg-muted/50 transition-smooth"
          onClick={() => onSelectConversation?.(undefined)}
        >
          <Settings className="h-4 w-4" />
          <span className="text-sm">Settings</span>
        </Button>
      </div>
    </div>
  );
};
