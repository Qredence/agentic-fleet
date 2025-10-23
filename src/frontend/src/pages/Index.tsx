import { ChatContainer } from "@/components/ChatContainer";
import { ChatSidebar } from "@/components/ChatSidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ThemeSwitch } from "@/components/ui/theme-switch-button";
import logoDark from "@/public/logo-darkmode.svg";
import logoLight from "@/public/logo-lightmode.svg";
import { History } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const Index = () => {
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const updateTheme = () => {
      setIsDark(document.documentElement.classList.contains("dark"));
    };
    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const handleSelectConversation = useCallback((id?: string) => {
    setConversationId(id);
  }, []);

  const handleConversationChange = useCallback((id?: string) => {
    setConversationId(id);
  }, []);

  return (
    <div className="flex h-screen w-full bg-background">
      <div className="absolute top-4 left-4 z-10">
        <img src={isDark ? logoDark : logoLight} alt="Logo" className="h-6 w-auto" />
      </div>

      <div className="absolute top-4 right-16 z-10">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="hover:bg-muted/50">
              <History className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80 p-0">
            <ChatSidebar
              selectedConversationId={conversationId}
              onSelectConversation={handleSelectConversation}
            />
          </SheetContent>
        </Sheet>
      </div>

      <div className="absolute top-4 right-4 z-10">
        <ThemeSwitch />
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-[800px] h-full">
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
