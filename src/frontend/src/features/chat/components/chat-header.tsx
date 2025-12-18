import { cn } from "@/lib/utils";

export type ChatHeaderProps = {
  title: string;
  sidebarTrigger?: React.ReactNode;
  actions?: React.ReactNode;
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
        "z-10 flex h-16 w-full shrink-0 items-center gap-2 px-4",
        className,
      )}
      style={{ background: "unset", backgroundColor: "unset" }}
    >
      {sidebarTrigger}
      <div className="flex min-w-0 flex-1 flex-col items-center justify-between gap-2">
        <div
          className="text-foreground truncate text-center"
          style={{ width: "264px" }}
        >
          {title}
        </div>
        {actions ? (
          <div className="flex shrink-0 items-center gap-1">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
