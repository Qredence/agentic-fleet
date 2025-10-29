/**
 * ChatPlanDisplay Component
 *
 * Displays execution plans in a clean, organized format:
 * - Plan title and description
 * - Step-by-step plan items
 * - Streaming state indicators
 * - Collapsible/expandable functionality
 */

import { memo, useState, useCallback } from "react";
import { Badge } from "@/components/ui/shadcn/badge";
import { Button } from "@/components/ui/shadcn/button";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  CheckCircle,
  Circle,
} from "lucide-react";
import type { Plan as PlanType } from "@/lib/hooks/useChatState";

interface ChatPlanDisplayProps {
  plan: PlanType | null;
  className?: string;
}

const ChatPlanDisplayComponent = ({
  plan,
  className = "",
}: ChatPlanDisplayProps) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleToggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  if (!plan) {
    return null;
  }

  return (
    <div className={`border rounded-lg bg-muted/30 ${className}`}>
      {/* Plan Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={handleToggleExpanded}
      >
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={(e) => {
              e.stopPropagation();
              handleToggleExpanded();
            }}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>

          <div className="flex items-center gap-2">
            {plan.isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            ) : (
              <CheckCircle className="h-4 w-4 text-green-500" />
            )}
            <h3 className="font-semibold text-foreground">{plan.title}</h3>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={plan.isStreaming ? "default" : "secondary"}>
            {plan.isStreaming ? "Active" : "Complete"}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {plan.steps.length} steps
          </Badge>
        </div>
      </div>

      {/* Plan Content */}
      {isExpanded && (
        <div className="border-t">
          <div className="p-4 space-y-3">
            {plan.description && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {plan.description}
              </p>
            )}

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-foreground mb-3">
                Execution Steps:
              </h4>
              {plan.steps.map((step, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-3 rounded-md bg-background/50 hover:bg-background transition-colors"
                >
                  <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 flex-shrink-0 mt-0.5">
                    {plan.isStreaming ? (
                      <Circle className="h-3 w-3 text-primary" />
                    ) : (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed text-foreground">
                      {step}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <Badge variant="outline" className="text-xs">
                      Step {index + 1}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            {plan.isStreaming && (
              <div className="flex items-center gap-2 pt-2 border-t">
                <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                <span className="text-xs text-muted-foreground">
                  Plan is being updated...
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const ChatPlanDisplay = memo(ChatPlanDisplayComponent);
