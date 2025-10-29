import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/shadcn/alert";
import { Button } from "@/components/ui/shadcn/button";
import { ConnectionStatus } from "@/lib/use-fastapi-chat";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Loader2, WifiOff } from "lucide-react";

interface ConnectionStatusIndicatorProps {
  status: ConnectionStatus;
  onRetry?: () => void;
  className?: string;
}

/**
 * Connection status indicator component
 *
 * Displays the current backend connection status with appropriate styling
 * and actions. Follows WCAG 2.1 AA guidelines with proper ARIA attributes.
 *
 * @example
 * ```tsx
 * <ConnectionStatusIndicator
 *   status={connectionStatus}
 *   onRetry={checkHealth}
 * />
 * ```
 */
export const ConnectionStatusIndicator = ({
  status,
  onRetry,
  className,
}: ConnectionStatusIndicatorProps) => {
  // Only show alert for disconnected or connecting states
  if (status === "connected") {
    return null;
  }

  const isConnecting = status === "connecting";
  const isDisconnected = status === "disconnected";

  return (
    <Alert
      variant={isDisconnected ? "destructive" : "default"}
      className={cn("mb-4", className)}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center gap-2">
        {isConnecting && (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        )}
        {isDisconnected && <WifiOff className="h-4 w-4" aria-hidden="true" />}
        <div className="flex-1">
          <AlertTitle className="mb-1">
            {isConnecting && "Connecting to backend..."}
            {isDisconnected && "Backend Connection Lost"}
          </AlertTitle>
          <AlertDescription className="text-sm">
            {isConnecting && (
              <span>
                Attempting to establish connection with the AgenticFleet backend
                server.
              </span>
            )}
            {isDisconnected && (
              <span>
                Unable to reach the backend server. Please ensure the backend is
                running on{" "}
                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                  localhost:8000
                </code>
              </span>
            )}
          </AlertDescription>
        </div>
        {isDisconnected && onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="shrink-0"
            aria-label="Retry connection"
          >
            Retry
          </Button>
        )}
      </div>
    </Alert>
  );
};

/**
 * Compact connection status badge for toolbar/header
 *
 * Displays a minimal status indicator suitable for persistent display
 * in the application header or toolbar.
 */
export const ConnectionStatusBadge = ({
  status,
  onRetry,
  className,
}: ConnectionStatusIndicatorProps) => {
  const statusConfig = {
    connected: {
      icon: CheckCircle2,
      label: "Connected",
      className: "text-green-600 dark:text-green-400",
      ariaLabel: "Backend connected",
      animate: false,
    },
    connecting: {
      icon: Loader2,
      label: "Connecting",
      className: "text-amber-600 dark:text-amber-400",
      ariaLabel: "Connecting to backend",
      animate: true,
    },
    disconnected: {
      icon: AlertCircle,
      label: "Disconnected",
      className: "text-red-600 dark:text-red-400",
      ariaLabel: "Backend disconnected",
      animate: false,
    },
  } as const;

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md transition-colors",
        config.className,
        status === "disconnected" && "cursor-pointer hover:bg-muted/50",
        className,
      )}
      onClick={status === "disconnected" && onRetry ? onRetry : undefined}
      role="status"
      aria-label={config.ariaLabel}
      tabIndex={status === "disconnected" ? 0 : undefined}
      onKeyDown={(e) => {
        if (
          status === "disconnected" &&
          onRetry &&
          (e.key === "Enter" || e.key === " ")
        ) {
          e.preventDefault();
          onRetry();
        }
      }}
    >
      <Icon
        className={cn("h-3 w-3", config.animate && "animate-spin")}
        aria-hidden="true"
      />
      <span>{config.label}</span>
    </div>
  );
};
