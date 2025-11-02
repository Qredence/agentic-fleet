import { Loader } from "@/components/ui/loader";

/** Loading indicator component for streaming states */
export function LoadingIndicator() {
  return <Loader variant="loading-dots" text="Agent is thinking" />;
}
