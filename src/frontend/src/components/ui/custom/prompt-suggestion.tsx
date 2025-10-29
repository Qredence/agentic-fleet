import { cn } from "@/lib/utils";

interface PromptSuggestionsProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function PromptSuggestions({
  children,
  className,
  ...props
}: PromptSuggestionsProps) {
  return (
    <div className={cn("flex flex-wrap gap-2 py-2", className)} {...props}>
      {children}
    </div>
  );
}

interface PromptSuggestionProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export function PromptSuggestion({
  icon,
  children,
  className,
  ...props
}: PromptSuggestionProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium",
        "bg-card text-foreground border border-border",
        "hover:bg-accent hover:text-accent-foreground",
        "transition-smooth",
        className,
      )}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </button>
  );
}
