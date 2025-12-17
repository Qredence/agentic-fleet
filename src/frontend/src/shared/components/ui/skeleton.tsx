import { cn } from "@/shared/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Animation variant */
  variant?: "pulse" | "shimmer" | "wave";
  /** Shape of the skeleton */
  shape?: "text" | "circle" | "rectangle";
}

export function Skeleton({
  className,
  variant = "shimmer",
  shape = "rectangle",
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(
        "bg-muted relative overflow-hidden",
        // Shape variants
        shape === "circle" && "rounded-full",
        shape === "text" && "rounded h-4",
        shape === "rectangle" && "rounded-lg",
        // Animation variants
        variant === "pulse" && "animate-pulse",
        variant === "shimmer" &&
          "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-linear-to-r before:from-transparent before:via-white/10 before:to-transparent",
        variant === "wave" &&
          "after:absolute after:inset-0 after:animate-[wave_1.6s_linear_0.5s_infinite] after:bg-linear-to-r after:from-transparent after:via-white/5 after:to-transparent",
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  );
}

export function SkeletonText({
  lines = 3,
  className,
  ...props
}: { lines?: number } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          shape="text"
          className={cn(
            "h-4",
            // Make last line shorter for natural look
            i === lines - 1 && "w-3/4",
          )}
          style={{
            animationDelay: `${i * 100}ms`,
          }}
        />
      ))}
    </div>
  );
}

export function SkeletonAvatar({
  size = "md",
  className,
  ...props
}: {
  size?: "sm" | "md" | "lg";
} & React.HTMLAttributes<HTMLDivElement>) {
  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <Skeleton
      shape="circle"
      className={cn(sizeClasses[size], className)}
      {...props}
    />
  );
}
