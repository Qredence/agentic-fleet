import { Suspense, lazy } from "react";
import type { ComponentProps } from "react";
import * as PlanModule from "@/components/ai/plan";

// Lazy load Plan module
const PlanModuleLazy = lazy(() =>
  import("@/components/ai/plan").then((mod) => ({
    default: mod.Plan,
  })),
);

// Re-export other components directly (they're lightweight)
export const PlanContent = PlanModule.PlanContent;
export const PlanHeader = PlanModule.PlanHeader;
export const PlanTitle = PlanModule.PlanTitle;
export const PlanTrigger = PlanModule.PlanTrigger;

// Wrap Plan component with lazy loading
export const Plan = (props: ComponentProps<typeof PlanModule.Plan>) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PlanModuleLazy {...props} />
    </Suspense>
  );
};
