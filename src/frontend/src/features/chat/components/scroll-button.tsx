import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button-variants";
import { cn } from "@/lib/utils";
import { type VariantProps } from "class-variance-authority";
import { ChevronDown } from "lucide-react";

export type ScrollButtonProps = {
  className?: string;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  size?: VariantProps<typeof buttonVariants>["size"];
  isAtBottom: boolean;
  onClick: () => void;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick">;

function ScrollButton({
  className,
  variant = "outline",
  size = "sm",
  isAtBottom,
  onClick,
  ...props
}: ScrollButtonProps) {
  return (
    <Button
      variant={variant}
      size={size}
      className={cn(
        "h-10 w-10 rounded-full bg-background transition-all duration-150 ease-out",
        !isAtBottom
          ? "translate-y-0 scale-100 opacity-100"
          : "pointer-events-none translate-y-4 scale-95 opacity-0",
        className,
      )}
      onClick={onClick}
      aria-label="Scroll to bottom"
      aria-hidden={isAtBottom}
      tabIndex={isAtBottom ? -1 : 0}
      {...props}
    >
      <ChevronDown className="h-5 w-5 text-foreground" />
    </Button>
  );
}

export { ScrollButton };
