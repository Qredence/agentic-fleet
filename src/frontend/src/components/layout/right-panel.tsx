import { cn } from "@/lib/utils";
import { PanelRight } from "lucide-react";
import { Button } from "@/components/ui/button";

type RightPanelProps = {
  open: boolean;
  children: React.ReactNode;
  onOpenChange?: (open: boolean) => void;
};

/**
 * A simple collapsible right panel with floating style.
 * Uses CSS transitions for smooth open/close animations.
 * Matches the sidebar's floating variant styling.
 * Panel is fully externally controlled via the open prop.
 */
export function RightPanel({ open, children }: RightPanelProps) {
  return (
    <aside
      data-state={open ? "open" : "closed"}
      className={cn(
        "hidden md:flex flex-col transition-all duration-200 ease-linear overflow-hidden shrink-0 p-2",
        open ? "w-48" : "w-0 p-0",
      )}
    >
      <div
        className={cn(
          "flex h-full w-full flex-col rounded-lg border border-sidebar-border bg-sidebar shadow transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
      >
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </aside>
  );
}

/**
 * Trigger button to toggle the right panel.
 */
export function RightPanelTrigger({
  open,
  onOpenChange,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  className?: string;
}) {
  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn("h-7 w-7", className)}
      onClick={() => onOpenChange(!open)}
      aria-label={open ? "Close right panel" : "Open right panel"}
      aria-pressed={open}
    >
      <PanelRight
        className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
      />
      <span className="sr-only">Toggle Right Panel</span>
    </Button>
  );
}
