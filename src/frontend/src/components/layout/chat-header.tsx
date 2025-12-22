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
        "z-10 flex h-14 w-full shrink-0 items-center gap-2 px-4 border-b border-border",
        className,
      )}
    >
      {sidebarTrigger}
      <div className="flex flex-col justify-start items-center flex-1 min-w-0 ml-2">
        <h1 className="text-sm font-medium text-foreground truncate w-fit max-w-[264px]">
          {title}
        </h1>
      </div>
      {actions && (
        <div className="flex shrink-0 items-center gap-1">{actions}</div>
      )}
    </header>
  );
}
