import { cn } from "@/lib/utils";
import { ChevronDown, Lightbulb } from "lucide-react";
import { useState } from "react";

interface ReasoningProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function Reasoning({ children, defaultOpen = false, className, ...props }: ReasoningProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-muted/30 overflow-hidden transition-smooth",
        className
      )}
      {...props}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 p-3 text-left hover:bg-muted/50 transition-smooth"
      >
        <Lightbulb className="h-4 w-4 text-muted-foreground shrink-0" />
        <span className="text-sm font-medium text-foreground flex-1">Reasoning</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </button>
      {isOpen && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}

interface ReasoningTitleProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function ReasoningTitle({ children, className, ...props }: ReasoningTitleProps) {
  return (
    <div className={cn("text-sm font-semibold text-foreground mb-2", className)} {...props}>
      {children}
    </div>
  );
}

interface ReasoningContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function ReasoningContent({ children, className, ...props }: ReasoningContentProps) {
  return (
    <div className={cn("text-sm text-muted-foreground leading-relaxed", className)} {...props}>
      {children}
    </div>
  );
}
