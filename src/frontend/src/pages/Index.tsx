import { ChatContainer } from "@/components/features/chat";
import { useCallback, useState } from "react";

const Index = () => {
  const [conversationId, setConversationId] = useState<string | undefined>();

  const handleConversationChange = useCallback((id?: string) => {
    setConversationId(id);
  }, []);

  return (
    <div className="flex h-screen w-full bg-background">
      <ChatContainer
        conversationId={conversationId}
        onConversationChange={handleConversationChange}
      />
    </div>
  );
};

export default Index;
