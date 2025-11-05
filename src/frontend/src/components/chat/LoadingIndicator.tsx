import { TextShimmer } from "@/components/ui/text-shimmer";

/** Loading indicator component for streaming states */
export function LoadingIndicator() {
  return (
    <div className="mx-auto w-full max-w-[700px]">
      <div className="rounded-3xl border border-dashed border-muted p-4 text-center">
        <TextShimmer className="text-sm font-medium text-muted-foreground">
          Agent is thinking . . .
        </TextShimmer>
      </div>
    </div>
  );
}
