import { cn } from "@/lib/utils";

export interface LoaderProps {
  variant?: "text-shimmer";
  size?: "sm" | "md" | "lg";
  text?: string;
  className?: string;
}

export function TextShimmerLoader({
  text = "Thinking",
  className,
  size = "md",
}: {
  text?: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const textSizes = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  return (
    <div
      className={cn(
        "bg-[linear-gradient(to_right,var(--muted-foreground)_40%,var(--foreground)_60%,var(--muted-foreground)_80%)]",
        "bg-size-[200%_auto] bg-clip-text font-medium text-transparent",
        "animate-[shimmer_4s_infinite_linear]",
        textSizes[size],
        className
      )}
    >
      {text}
    </div>
  );
}

function Loader({ size = "md", text, className }: LoaderProps) {
  return <TextShimmerLoader text={text} size={size} className={className} />;
}

export { Loader };
