import { useEffect } from "react";
import { FullChatApp } from "@/components/blocks/full-chat-app";
import { useChatStore } from "@/stores";

function App() {
  const loadConversations = useChatStore((state) => state.loadConversations);

  // Initial load
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return <FullChatApp />;
}

export default App;
