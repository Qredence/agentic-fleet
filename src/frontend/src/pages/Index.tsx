import { ChatContainer } from "@/components/features/chat";
import { useCallback, useState } from "react";

const Index = () => {
  const [conversationId, setConversationId] = useState<string | undefined>();

  const handleConversationChange = useCallback((id?: string) => {
    setConversationId(id);
  }, []);

  return (
    <div className="flex h-screen w-full bg-background">
      <div className="flex-1 px-4 py-6">
        <div className="mx-auto h-full w-full max-w-5xl">
          <ChatContainer
            conversationId={conversationId}
            onConversationChange={handleConversationChange}
          />
        </div>
      </div>
    </div>
  );
};

export default Index;
