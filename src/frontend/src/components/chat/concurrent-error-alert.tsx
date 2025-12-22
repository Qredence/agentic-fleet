import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui";

export type ConcurrentErrorAlertProps = {
  onTerminate: () => void;
};

export function ConcurrentErrorAlert({
  onTerminate,
}: ConcurrentErrorAlertProps) {
  return (
    <div className="px-4 pt-4">
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Concurrent Execution Detected</AlertTitle>
        <AlertDescription className="flex items-center gap-4">
          Another workflow is currently running for this conversation.
          <Button
            variant="outline"
            size="sm"
            onClick={onTerminate}
            className="bg-background text-foreground hover:bg-accent"
          >
            Terminate Active Workflow
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  );
}
