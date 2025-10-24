import { ThemeSwitch } from "@/components/ui/custom/theme-switch-button";
import { Button } from "@/components/ui/shadcn/button";
import { DropdownMenu } from "@/components/ui/shadcn/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/shadcn/sheet";
import { GitBranch, History, Workflow } from "lucide-react";
import { ChatSidebar } from "./ChatSidebar";

interface ChatHeaderProps {
  logoSrc: string;
  statusLabel: string;
  selectedWorkflowLabel: string;
  selectedModel: string;
  activeConversationId?: string;
  onModelChange: (model: string) => void;
  onSelectConversation: (conversationId?: string) => void;
}

export const ChatHeader = ({
  logoSrc,
  statusLabel,
  selectedWorkflowLabel,
  selectedModel,
  activeConversationId,
  onModelChange,
  onSelectConversation,
}: ChatHeaderProps) => {
  const WorkflowIcon = selectedModel === "magentic_fleet" ? Workflow : GitBranch;

  return (
    <header className="fixed inset-x-0 top-0 z-20 border-b border-border/60  px-6 py-3 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-6">
        <div className="flex items-center gap-3 flex-shrink-0">
          <img src={logoSrc} alt="AgenticFleet logo" className="h-6 w-auto" />
          <div className="flex flex-row items-center justify-start gap-[7px]">
            <span className="text-lg font-semibold text-foreground">AgenticFleet</span>
            <span className="text-xs text-muted-foreground">{statusLabel}</span>
          </div>
        </div>

        <div className="flex items-center justify-center flex-shrink-0">
          <div className="inline-flex items-center justify-center gap-3 rounded-full px-4 py-1 shadow-lg backdrop-blur border border-[hsl(var(--header-border))]">
            <div className="flex items-center gap-2">
              <WorkflowIcon className="h-4 w-4 text-foreground" />
              <DropdownMenu
                className="h-9 min-w-[200px] justify-between rounded-full border-none bg-transparent px-2 text-sm font-medium text-foreground shadow-none hover:bg-transparent"
                options={[
                  {
                    label: "Magentic Fleet",
                    onClick: () => onModelChange("magentic_fleet"),
                    Icon: <Workflow className="h-4 w-4" />,
                  },
                  {
                    label: "Reflection & Retry",
                    onClick: () => onModelChange("workflow_as_agent"),
                    Icon: <GitBranch className="h-4 w-4" />,
                  },
                ]}
              >
                {selectedWorkflowLabel}
              </DropdownMenu>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center flex-shrink-0 rounded-full p-1 border border-[hsl(var(--header-border))]">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full hover:bg-muted/50">
                <History className="h-5 w-5" />
                <span className="sr-only">Open conversation history</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0">
              <ChatSidebar
                selectedConversationId={activeConversationId}
                onSelectConversation={onSelectConversation}
              />
            </SheetContent>
          </Sheet>
          <ThemeSwitch className="text-foreground" />
        </div>
      </div>
    </header>
  );
};
