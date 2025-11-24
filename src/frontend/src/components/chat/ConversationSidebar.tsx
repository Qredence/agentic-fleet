/**
 * ConversationSidebar Component
 * Sidebar for managing conversations
 */

import { useEffect } from "react";
import { Button } from "@openai/apps-sdk-ui/components/Button";
import { Plus, MessageCircle } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";

export function ConversationSidebar() {
  const {
    conversations,
    currentConversationId,
    isLoading,
    loadConversations,
    createConversation,
    selectConversation,
  } = useChatStore();

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleSelectConversation = async (id: string) => {
    await selectConversation(id);
  };

  const handleNewConversation = async () => {
    try {
      await createConversation("New Conversation");
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  };

  return (
    <div className="flex h-full w-64 flex-col border-r border-default bg-surface">
      {/* Header */}
      <div className="border-b border-default p-4">
        <Button
          onClick={handleNewConversation}
          disabled={isLoading}
          color="primary"
          block
          className="justify-center"
        >
          <Plus className="size-4" />
          New Conversation
        </Button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 && !isLoading && (
          <div className="flex h-full items-center justify-center text-center p-4">
            <p className="text-sm text-secondary">
              No conversations yet.
              <br />
              Start a new one!
            </p>
          </div>
        )}

        <div className="space-y-1">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => handleSelectConversation(conversation.id)}
              className={`w-full rounded-lg p-3 text-left transition-colors ${
                conversation.id === currentConversationId
                  ? "bg-primary/10 border border-primary/20"
                  : "hover:bg-surface-hover border border-transparent"
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageCircle className="size-4 mt-0.5 shrink-0 text-secondary" />
                <div className="flex-1 min-w-0">
                  <div className="truncate text-sm font-medium">
                    {conversation.title}
                  </div>
                  <div className="text-xs text-secondary mt-0.5">
                    {conversation.messages.length} messages
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
