import { useEffect } from "react";
import { ChatApp, useChatStore } from "@/features/chat";

function App() {
  const loadConversations = useChatStore((state) => state.loadConversations);

  // Initial load
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return <ChatApp />;
}

export default App;
