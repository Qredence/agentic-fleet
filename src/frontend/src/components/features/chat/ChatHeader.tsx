/**
 * ChatHeader Component - Responsive Header with Flexbox Layout
 * 
 * Features:
 * - Responsive layout that adapts to mobile, tablet, and desktop
 * - Proper spacing and element positioning using Flexbox
 * - Optimized for different viewport sizes
 * - Clean visual hierarchy
 */

import { ThemeSwitch } from "@/components/ui/custom/theme-switch-button";
import { Button } from "@/components/ui/shadcn/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/shadcn/sheet";
import { History, Workflow, Activity } from "lucide-react";
import { ChatSidebar } from "./ChatSidebar";
import type { ConnectionStatus } from "@/lib/types";
import logoDark from "@/public/logo-darkmode.svg";
import logoLight from "@/public/logo-lightmode.svg";
import { useTheme } from "next-themes";

interface ChatHeaderProps {
  conversationId?: string;
  connectionStatus: ConnectionStatus;
  onCheckHealth: () => void;
}

export const ChatHeader = ({
  conversationId,
  connectionStatus,
  onCheckHealth,
}: ChatHeaderProps) => {
  const { theme } = useTheme();
  const logoSrc = theme === "dark" ? logoDark : logoLight;

  return (
    <header className="flex-shrink-0 border-b border-border/60 bg-background/95 backdrop-blur-sm">
      {/* Mobile and Tablet: Single row with optimized spacing */}
      <div className="flex items-center justify-between gap-2 px-3 py-2.5 sm:gap-4 sm:px-4 md:px-6 md:py-3">
        {/* Left: Logo and Title */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-shrink">
          <img 
            src={logoSrc} 
            alt="AgenticFleet logo" 
            className="h-5 w-auto sm:h-6 flex-shrink-0" 
          />
          <span className="text-base sm:text-lg font-semibold text-foreground truncate">
            AgenticFleet
          </span>
        </div>

        {/* Center: Workflow Badge (Hidden on mobile, visible on tablet+) */}
        <div className="hidden md:flex items-center justify-center flex-shrink-0">
          <div className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 shadow-sm border border-border/50 bg-background/80">
            <Workflow className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-medium text-foreground">
              Dynamic Orchestration
            </span>
          </div>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
          {/* Connection Status Indicator (visible on tablet+) */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onCheckHealth}
            className="hidden sm:flex h-8 w-8 rounded-full hover:bg-muted/50"
            title={`Connection: ${connectionStatus}`}
          >
            <Activity 
              className={`h-4 w-4 ${
                connectionStatus === "connected" 
                  ? "text-green-500" 
                  : connectionStatus === "disconnected"
                  ? "text-red-500"
                  : "text-yellow-500"
              }`} 
            />
            <span className="sr-only">Check connection</span>
          </Button>

          {/* History Sidebar */}
          <Sheet>
            <SheetTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8 rounded-full hover:bg-muted/50"
              >
                <History className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="sr-only">Open conversation history</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] sm:w-80 p-0">
              <ChatSidebar
                selectedConversationId={conversationId}
                onSelectConversation={() => {}}
              />
            </SheetContent>
          </Sheet>

          {/* Theme Switch */}
          <ThemeSwitch className="text-foreground h-8 w-8" />
        </div>
      </div>

      {/* Mobile-only: Workflow Badge on second row */}
      <div className="md:hidden border-t border-border/30 px-3 py-2 flex items-center justify-center">
        <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 bg-muted/50">
          <Workflow className="h-3 w-3 text-muted-foreground" />
          <span className="text-xs font-medium text-foreground">
            Dynamic Orchestration
          </span>
        </div>
      </div>
    </header>
  );
};
