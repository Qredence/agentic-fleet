import { useEffect, useState } from "react";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { ConversationsSidebar } from "@/components/chat/ConversationsSidebar";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { Menu } from "lucide-react";

/** Main chat page component */
export function ChatPage() {
  const { loadConversations, error } = useChatStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <ConversationsSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden md:ml-[280px]">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden"
              aria-label="Toggle sidebar"
            >
              <Menu size={20} />
            </Button>
            <h1 className="text-lg font-semibold">AgenticFleet Chat</h1>
          </div>
          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-1 text-sm text-destructive">
              {error}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-hidden">
          <ChatContainer />
        </div>
      </div>
    </div>
  );
}
