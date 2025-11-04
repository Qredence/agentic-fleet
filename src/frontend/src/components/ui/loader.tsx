import * as React from "react";
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const loaderVariants = cva("inline-flex items-center justify-center", {
  variants: {
    variant: {
      circular:
        "animate-spin rounded-full border-2 border-current border-t-transparent",
      classic: "animate-pulse rounded-md bg-muted",
      pulse: "animate-pulse",
      "pulse-dot": "relative h-2 w-2 rounded-full bg-current",
      dots: "flex gap-1",
      typing: "flex gap-1",
      wave: "flex gap-1 items-end",
      bars: "flex gap-1 items-end",
      terminal: "font-mono text-sm",
      "text-blink": "font-mono text-sm",
      "text-shimmer": "font-mono text-sm",
      "loading-dots": "font-mono text-sm",
    },
    size: {
      sm: "h-4 w-4 text-sm",
      md: "h-6 w-6 text-base",
      lg: "h-8 w-8 text-lg",
    },
  },
  defaultVariants: {
    variant: "circular",
    size: "md",
  },
});

export interface LoaderProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof loaderVariants> {
  text?: string;
}

const Loader = React.forwardRef<HTMLDivElement, LoaderProps>(
  ({ className, variant, size, text, ...props }, ref) => {
    const renderLoaderContent = () => {
      switch (variant) {
        case "dots":
          return (
            <>
              <div
                className="h-1 w-1 rounded-full bg-current animate-bounce"
                style={{ animationDelay: "0ms" }}
              />
              <div
                className="h-1 w-1 rounded-full bg-current animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <div
                className="h-1 w-1 rounded-full bg-current animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
            </>
          );

        case "typing":
          return (
            <>
              <div
                className="h-1 w-1 rounded-full bg-current animate-pulse"
                style={{ animationDelay: "0ms" }}
              />
              <div
                className="h-1 w-1 rounded-full bg-current animate-pulse"
                style={{ animationDelay: "200ms" }}
              />
              <div
                className="h-1 w-1 rounded-full bg-current animate-pulse"
                style={{ animationDelay: "400ms" }}
              />
            </>
          );

        case "wave":
          return (
            <>
              <div
                className="h-2 w-1 bg-current rounded animate-pulse"
                style={{ animationDelay: "0ms" }}
              />
              <div
                className="h-3 w-1 bg-current rounded animate-pulse"
                style={{ animationDelay: "100ms" }}
              />
              <div
                className="h-4 w-1 bg-current rounded animate-pulse"
                style={{ animationDelay: "200ms" }}
              />
              <div
                className="h-3 w-1 bg-current rounded animate-pulse"
                style={{ animationDelay: "300ms" }}
              />
              <div
                className="h-2 w-1 bg-current rounded animate-pulse"
                style={{ animationDelay: "400ms" }}
              />
            </>
          );

        case "bars":
          return (
            <>
              <div
                className="w-1 h-4 bg-current rounded animate-pulse"
                style={{ animationDelay: "0ms" }}
              />
              <div
                className="w-1 h-6 bg-current rounded animate-pulse"
                style={{ animationDelay: "150ms" }}
              />
              <div
                className="w-1 h-8 bg-current rounded animate-pulse"
                style={{ animationDelay: "300ms" }}
              />
              <div
                className="w-1 h-6 bg-current rounded animate-pulse"
                style={{ animationDelay: "450ms" }}
              />
              <div
                className="w-1 h-4 bg-current rounded animate-pulse"
                style={{ animationDelay: "600ms" }}
              />
            </>
          );

        case "pulse-dot":
          return (
            <div className="relative">
              <div className="h-2 w-2 rounded-full bg-current" />
              <div className="absolute inset-0 h-2 w-2 rounded-full bg-current animate-ping" />
            </div>
          );

        case "terminal":
          return (
            <span className="font-mono">
              $
              <span className="inline-block w-2 h-4 bg-current ml-1 animate-pulse" />
            </span>
          );

        case "text-blink":
          return (
            <span>
              Loading
              <span className="inline-block w-2 h-4 bg-current ml-1 animate-pulse" />
            </span>
          );

        case "text-shimmer":
          return (
            <span className="relative overflow-hidden">
              <span className="animate-pulse">Loading</span>
            </span>
          );

        case "loading-dots":
          return (
            <span>
              Loading
              <span className="inline-block animate-pulse">.</span>
              <span
                className="inline-block animate-pulse"
                style={{ animationDelay: "150ms" }}
              >
                .
              </span>
              <span
                className="inline-block animate-pulse"
                style={{ animationDelay: "300ms" }}
              >
                .
              </span>
            </span>
          );

        default:
          return null;
      }
    };

    return (
      <div
        ref={ref}
        className={cn(loaderVariants({ variant, size, className }))}
        {...props}
      >
        {renderLoaderContent()}
        {text && <span className="ml-2">{text}</span>}
      </div>
    );
  },
);
Loader.displayName = "Loader";

export { Loader };
