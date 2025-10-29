import { ChatContainer } from "@/components/features/chat";
import { useCallback, useState } from "react";

const Index = () => {
  const [conversationId, setConversationId] = useState<string | undefined>();

  const handleConversationChange = useCallback((id?: string) => {
    setConversationId(id);
  }, []);

  return (
    <div className="h-screen w-full overflow-hidden bg-background">
      <ChatContainer
        conversationId={conversationId}
        onConversationChange={handleConversationChange}
      />
    </div>
  );
};

export default Index;
