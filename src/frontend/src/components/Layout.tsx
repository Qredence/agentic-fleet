import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Menu } from "lucide-react";

interface Conversation {
  id: string;
  title: string;
  timestamp: Date;
  preview?: string;
}

interface LayoutProps {
  children: React.ReactNode;
  conversations?: Conversation[];
  activeConversationId?: string;
  onNewConversation?: () => void;
  onSelectConversation?: (id: string) => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  conversations = [],
  activeConversationId,
  onNewConversation,
  onSelectConversation,
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div
      className="min-h-screen flex overflow-hidden transition-colors duration-300"
      style={{
        backgroundColor: "var(--color-surface)",
        color: "var(--color-text)",
      }}
    >
      <Sidebar
        isOpen={isSidebarOpen}
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewConversation={onNewConversation}
        onSelectConversation={onSelectConversation}
      />

      <main
        className={`flex-1 flex flex-col h-screen transition-all duration-300 ease-in-out ${isSidebarOpen ? "ml-64" : "ml-0"}`}
      >
        {!isSidebarOpen && (
          <div className="absolute top-4 left-4 z-50">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 rounded-md transition-colors"
              style={{
                backgroundColor: "var(--color-surface-secondary)",
                color: "var(--color-text-secondary)",
                border: "1px solid var(--gray-200)",
              }}
            >
              <Menu size={20} />
            </button>
          </div>
        )}
        {children}
      </main>
    </div>
  );
};
