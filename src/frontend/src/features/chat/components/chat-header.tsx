import { cn } from "@/shared/lib/utils";

export type ChatHeaderProps = {
  title: string;
  sidebarTrigger?: React.ReactNode;
  className?: string;
};

export function ChatHeader({
  title,
  sidebarTrigger,
  className,
}: ChatHeaderProps) {
  return (
    <header
      className={cn(
        "bg-background z-10 flex h-16 w-full shrink-0 items-center gap-2 border-b px-4",
        className,
      )}
    >
      {sidebarTrigger}
      <div className="text-foreground truncate">{title}</div>
    </header>
  );
}
