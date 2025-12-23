import { cn } from "@/lib/utils";
import { PanelRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "motion/react";

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
    <motion.aside
      data-state={open ? "open" : "closed"}
      className={cn(
        "hidden md:flex flex-col overflow-hidden shrink-0 p-2",
        open ? "w-48" : "w-0 p-0",
      )}
      initial={false}
      animate={{
        width: open ? "12rem" : "0rem",
        padding: open ? "0.5rem" : "0rem",
      }}
      transition={{ duration: 0.2, ease: "linear" }}
    >
      <motion.div
        className={cn(
          "flex h-full w-full flex-col rounded-lg border border-sidebar-border bg-sidebar shadow",
          open ? "opacity-100" : "opacity-0",
        )}
        animate={{ opacity: open ? 1 : 0 }}
        transition={{ duration: 0.2 }}
      >
        <div className="flex-1 overflow-auto">{children}</div>
      </motion.div>
    </motion.aside>
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
      style={{ backgroundColor: "var(--color-background-secondary-soft)" }}
      onClick={() => onOpenChange(!open)}
      aria-label={open ? "Close right panel" : "Open right panel"}
      aria-pressed={open}
    >
      <motion.div
        animate={{ rotate: open ? 180 : 0 }}
        transition={{ duration: 0.15 }}
      >
        <PanelRight className="h-4 w-4" />
      </motion.div>
      <span className="sr-only">Toggle Right Panel</span>
    </Button>
  );
}
