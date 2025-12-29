import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ChatHeaderProps = {
  title: string;
  sidebarTrigger?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

export function ChatHeader({
  title,
  sidebarTrigger,
  actions,
  className,
}: ChatHeaderProps) {
  return (
    <header
      className={cn(
        "z-10 flex h-14 w-full shrink-0 items-center gap-2 px-4 my-2",
        className,
      )}
    >
      {sidebarTrigger}
      <div className="flex flex-col justify-start items-center flex-1 min-w-0 ml-2">
        <h1
          className="text-sm font-medium text-foreground truncate w-fit max-w-66 py-2 px-3 rounded-2xl"
          style={{ backgroundColor: "var(--color-background-secondary-soft)" }}
        >
          {title}
        </h1>
      </div>
      {actions && (
        <div className="flex shrink-0 items-center gap-1">{actions}</div>
      )}
    </header>
  );
}
