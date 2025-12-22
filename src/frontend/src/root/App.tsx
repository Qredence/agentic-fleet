import { useEffect } from "react";
import { ChatPage } from "@/pages/chat-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { useChatStore } from "@/stores";
import { useShallow } from "zustand/shallow";

import { SidebarProvider } from "@/components/ui/sidebar";

function App() {
  const { loadConversations, activeView } = useChatStore(
    useShallow((state) => ({
      loadConversations: state.loadConversations,
      activeView: state.activeView,
    })),
  );

  // Initial load
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // View routing based on store state
  return (
    <SidebarProvider>
      {activeView === "dashboard" ? <DashboardPage /> : <ChatPage />}
    </SidebarProvider>
  );
}

export default App;
