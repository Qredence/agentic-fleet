import {
  Steps,
  StepsContent,
  StepsItem,
  StepsTrigger,
} from "@/components/ui/steps";
import type { StepItem } from "@/types/chat";
import { ListChecks } from "lucide-react";

interface StepsDisplayProps {
  steps: StepItem[];
  isStreaming?: boolean;
  defaultOpen?: boolean;
  title?: string;
}

/**
 * StepsDisplay component wraps PromptKit Steps to display task plans
 * and step-by-step workflows from orchestrator messages
 */
export function StepsDisplay({
  steps,
  isStreaming = false,
  defaultOpen = true,
  title = "Plan",
}: StepsDisplayProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <Steps defaultOpen={defaultOpen || isStreaming}>
      <StepsTrigger leftIcon={<ListChecks className="size-4" />}>
        {title} ({steps.length} {steps.length === 1 ? "step" : "steps"})
      </StepsTrigger>
      <StepsContent>
        <div className="space-y-2">
          {steps.map((step, index) => (
            <div key={`step-${step.index}-${index}`}>
              <StepsItem className="flex items-start gap-2">
                <span className="font-medium text-foreground">
                  {step.label ? `${step.label}.` : `${step.index + 1}.`}
                </span>
                <span className="flex-1">{step.content}</span>
              </StepsItem>
              {step.substeps && step.substeps.length > 0 && (
                <div className="ml-6 mt-1 space-y-1">
                  {step.substeps.map((substep, subIndex) => (
                    <StepsItem
                      key={`substep-${step.index}-${subIndex}`}
                      className="text-xs"
                    >
                      <span className="text-muted-foreground">
                        {String.fromCharCode(97 + substep.index)}.
                      </span>{" "}
                      {substep.content}
                    </StepsItem>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </StepsContent>
    </Steps>
  );
}
