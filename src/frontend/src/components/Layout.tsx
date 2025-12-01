import { Sidebar } from "./Sidebar";
import type { Conversation } from "../api/types";

interface LayoutProps {
  children: React.ReactNode;
  onNewChat?: () => void;
  conversations?: Conversation[];
  currentConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  onNewChat,
  conversations,
  currentConversationId,
  onSelectConversation,
}) => {
  return (
    <div className="flex h-screen bg-gray-1000 text-gray-100 overflow-hidden font-sans">
      <Sidebar
        onNewChat={onNewChat}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={onSelectConversation}
      />
      <main className="flex-1 flex flex-col min-w-0 bg-gray-1000">
        {children}
      </main>
    </div>
  );
};
