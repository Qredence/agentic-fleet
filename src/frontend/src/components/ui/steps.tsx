import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

interface StepsProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Steps({ children, className, ...props }: StepsProps) {
  return (
    <div className={cn("flex flex-col gap-2 py-2", className)} {...props}>
      {children}
    </div>
  );
}

interface StepProps extends React.HTMLAttributes<HTMLDivElement> {
  status?: "pending" | "current" | "complete" | "error";
  children: React.ReactNode;
}

export function Step({ status = "pending", children, className, ...props }: StepProps) {
  const statusConfig = {
    pending: {
      icon: <Circle className="h-4 w-4 text-muted-foreground" />,
      textColor: "text-muted-foreground",
    },
    current: {
      icon: <Loader2 className="h-4 w-4 animate-spin text-primary" />,
      textColor: "text-foreground font-medium",
    },
    complete: {
      icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
      textColor: "text-muted-foreground",
    },
    error: {
      icon: <XCircle className="h-4 w-4 text-destructive" />,
      textColor: "text-destructive",
    },
  };

  const config = statusConfig[status];

  return (
    <div className={cn("flex items-center gap-3", className)} {...props}>
      <div className="shrink-0">{config.icon}</div>
      <div className={cn("text-sm", config.textColor)}>{children}</div>
    </div>
  );
}
