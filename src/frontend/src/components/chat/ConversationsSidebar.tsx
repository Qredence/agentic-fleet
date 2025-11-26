import { useEffect } from "react";
import { MessageSquare, Plus, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils";

interface ConversationsSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

/** Sidebar component displaying list of conversations */
export function ConversationsSidebar({
  isOpen = true,
  onClose,
}: ConversationsSidebarProps) {
  const {
    conversations,
    isLoading,
    currentConversationId,
    loadConversations,
    selectConversation,
    createConversation,
  } = useChatStore();

  // Load conversations on mount
  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const handleNewConversation = async () => {
    try {
      await createConversation("New Conversation");
      // Close sidebar on mobile after creating new conversation
      if (onClose) {
        onClose();
      }
    } catch (error) {
      // Error is handled by store
      console.error("Failed to create new conversation:", error);
    }
  };

  const handleConversationClick = async (id: string) => {
    if (id === currentConversationId) {
      return; // Already on this conversation
    }
    try {
      await selectConversation(id);
      // Close sidebar on mobile after switching
      if (onClose) {
        onClose();
      }
    } catch (error) {
      // Error is handled by store
      console.error("Failed to switch conversation:", error);
    }
  };

  const getConversationPreview = (conv: (typeof conversations)[0]) => {
    if (conv.messages && conv.messages.length > 0) {
      const lastMessage = conv.messages[conv.messages.length - 1];
      // Truncate preview to 50 characters
      const preview = lastMessage.content.slice(0, 50);
      return preview.length < lastMessage.content.length
        ? `${preview}...`
        : preview;
    }
    return "New conversation";
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen w-[280px] border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-300 ease-in-out",
        "flex flex-col",
        // Mobile: overlay, desktop: persistent
        isOpen ? "translate-x-0" : "-translate-x-full",
        "md:translate-x-0", // Always visible on desktop
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sidebar-border p-4">
        <h2 className="text-lg font-semibold">Conversations</h2>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="md:hidden"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </Button>
        )}
      </div>

      {/* New Conversation Button */}
      <div className="border-b border-sidebar-border p-4">
        <Button
          onClick={handleNewConversation}
          className="w-full justify-start gap-2"
          variant="default"
        >
          <Plus size={18} />
          New Conversation
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <MessageSquare className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Start a new conversation to get started
            </p>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conv) => {
              const isActive = conv.id === currentConversationId;
              return (
                <button
                  key={conv.id}
                  onClick={() => handleConversationClick(conv.id)}
                  className={cn(
                    "w-full rounded-lg px-3 py-2 text-left transition-colors",
                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    isActive &&
                      "bg-sidebar-primary text-sidebar-primary-foreground",
                  )}
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-start justify-between gap-2">
                      <span
                        className={cn(
                          "truncate text-sm font-medium",
                          isActive ? "text-sidebar-primary-foreground" : "",
                        )}
                      >
                        {conv.title || "Untitled Conversation"}
                      </span>
                      <span
                        className={cn(
                          "shrink-0 text-xs",
                          isActive
                            ? "text-sidebar-primary-foreground/70"
                            : "text-muted-foreground",
                        )}
                      >
                        {formatDate(conv.created_at)}
                      </span>
                    </div>
                    {conv.messages && conv.messages.length > 0 && (
                      <p
                        className={cn(
                          "truncate text-xs",
                          isActive
                            ? "text-sidebar-primary-foreground/70"
                            : "text-muted-foreground",
                        )}
                      >
                        {getConversationPreview(conv)}
                      </p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
