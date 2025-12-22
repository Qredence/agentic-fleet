import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui";
import { PromptInputAction } from "./prompt-input";
import { cn } from "@/lib/utils";

export type ToggleButtonProps = {
  value: boolean;
  onChange: (value: boolean) => void;
  icon?: LucideIcon;
  label?: string;
  tooltipTitle: string;
  tooltipDescription: string;
  disabled?: boolean;
  size?: "sm" | "icon";
  className?: string;
  iconClassName?: string;
};

export function ToggleButton({
  value,
  onChange,
  icon: Icon,
  label,
  tooltipTitle,
  tooltipDescription,
  disabled = false,
  size = "sm",
  className,
  iconClassName,
}: ToggleButtonProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(!value);
  };

  const buttonClassName =
    size === "icon"
      ? "size-8 rounded-full transition-all duration-200"
      : "h-8 gap-1.5 px-2.5 rounded-full transition-all duration-200";

  return (
    <PromptInputAction
      tooltip={
        <div className="flex flex-col gap-1">
          <div className="font-medium">{tooltipTitle}</div>
          <div className="text-xs text-muted-foreground">
            {tooltipDescription}
          </div>
        </div>
      }
    >
      <Button
        variant="ghost"
        size={size}
        className={cn(
          buttonClassName,
          value
            ? "text-foreground bg-secondary"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary/80",
          className,
        )}
        onClick={handleClick}
        aria-label={
          value ? `Disable ${tooltipTitle}` : `Enable ${tooltipTitle}`
        }
        aria-pressed={value}
        disabled={disabled}
      >
        {Icon && (
          <Icon
            className={cn(
              size === "icon" ? "size-4" : "size-3.5",
              value && "fill-current",
              iconClassName,
            )}
          />
        )}
        {label && <span className="text-xs font-medium">{label}</span>}
      </Button>
    </PromptInputAction>
  );
}
