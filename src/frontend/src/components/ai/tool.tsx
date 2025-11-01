import { cn } from "@/lib/utils";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

interface ToolProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  status?: "running" | "complete" | "error";
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export function Tool({
  name,
  status = "running",
  icon,
  children,
  className,
  ...props
}: ToolProps) {
  const statusIcons = {
    running: <Loader2 className="h-4 w-4 animate-spin text-primary" />,
    complete: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    error: <XCircle className="h-4 w-4 text-destructive" />,
  };

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-border bg-card p-3 transition-smooth",
        className,
      )}
      {...props}
    >
      <div className="shrink-0 mt-0.5">{icon || statusIcons[status]}</div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-foreground mb-1">{name}</div>
        {children && (
          <div className="text-xs text-muted-foreground">{children}</div>
        )}
      </div>
    </div>
  );
}
