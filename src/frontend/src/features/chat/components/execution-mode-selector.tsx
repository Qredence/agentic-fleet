import { Wand2, Rabbit, Workflow } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui";
import { PromptInputAction } from "./prompt-input";
import type { ExecutionMode } from "@/lib/constants";

export type ExecutionModeSelectorProps = {
  value: ExecutionMode;
  onChange: (value: ExecutionMode) => void;
};

const EXECUTION_MODE_CONFIG = [
  {
    value: "auto" as const,
    icon: Wand2,
    label: "Smart",
    description: "Auto-routes to best path",
    tooltipDescription: "Auto: Smart routing",
  },
  {
    value: "fast" as const,
    icon: Rabbit,
    label: "Quick",
    description: "Direct LLM response",
    tooltipDescription: "Fast: Fast path only",
  },
  {
    value: "standard" as const,
    icon: Workflow,
    label: "Full",
    description: "Complete agent workflow",
    tooltipDescription: "Standard: Full workflow",
  },
] as const;

export function ExecutionModeSelector({
  value,
  onChange,
}: ExecutionModeSelectorProps) {
  const currentMode = EXECUTION_MODE_CONFIG.find(
    (mode) => mode.value === value,
  );
  const Icon = currentMode?.icon ?? Wand2;

  return (
    <PromptInputAction
      tooltip={
        <div className="flex flex-col gap-1">
          <div className="font-medium">Execution Mode</div>
          <div className="text-xs text-muted-foreground">
            {currentMode?.tooltipDescription}
          </div>
        </div>
      }
    >
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger
          className="h-8 gap-1.5 px-3 rounded-full border-0 shadow-none text-muted-foreground hover:text-foreground hover:bg-secondary/80 focus:ring-2 focus:ring-foreground/10 focus:ring-offset-2 w-auto transition-all duration-200"
          aria-label={`Execution mode: ${value}`}
          onClick={(e) => e.stopPropagation()}
        >
          <span className="flex items-center gap-1.5">
            <Icon className="size-3.5" />
            <span className="text-xs font-medium">{currentMode?.label}</span>
          </span>
        </SelectTrigger>
        <SelectContent side="top" align="start" className="min-w-44">
          {EXECUTION_MODE_CONFIG.map((mode) => {
            const ModeIcon = mode.icon;
            return (
              <SelectItem
                key={mode.value}
                value={mode.value}
                className="cursor-pointer"
              >
                <span className="flex items-center gap-2.5">
                  <ModeIcon className="size-4" />
                  <div className="flex flex-col gap-0.5">
                    <span className="font-medium">{mode.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {mode.description}
                    </span>
                  </div>
                </span>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </PromptInputAction>
  );
}
