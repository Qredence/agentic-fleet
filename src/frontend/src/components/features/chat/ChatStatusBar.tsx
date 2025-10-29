/**
 * ChatStatusBar Component - Responsive Status Display
 *
 * Displays status information about the chat session:
 * - Connection status indicator
 * - Current chat status
 * - Error messages
 * - Queue status information
 *
 * Responsive Features:
 * - Compact layout on mobile
 * - Hide non-essential info on small screens
 * - Flexible spacing with Flexbox
 */

import { memo } from "react";
import { Badge } from "@/components/ui/shadcn/badge";
import { AlertCircle, Loader2, Wifi, WifiOff } from "lucide-react";
import type { ConnectionStatus, ChatStatus, QueueStatus } from "@/lib/types";

interface ChatStatusBarProps {
  connectionStatus: ConnectionStatus;
  chatStatus: ChatStatus;
  error?: Error | null;
  queueStatus?: QueueStatus | null;
  className?: string;
}

const ChatStatusBarComponent = ({
  connectionStatus,
  chatStatus,
  error,
  queueStatus,
  className = "",
}: ChatStatusBarProps) => {
  const getStatusColor = (status: ChatStatus) => {
    switch (status) {
      case "ready":
        return "bg-green-500";
      case "submitted":
        return "bg-blue-500";
      case "streaming":
        return "bg-purple-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusText = (status: ChatStatus) => {
    switch (status) {
      case "ready":
        return "Ready";
      case "submitted":
        return "Submitted";
      case "streaming":
        return "Processing";
      case "error":
        return "Error";
      default:
        return "Unknown";
    }
  };

  return (
    <div
      className={`flex items-center justify-between px-3 py-2 sm:px-4 bg-background/95 ${className}`}
    >
      {/* Left: Status Indicators - Always visible */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
        {/* Connection Status */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {connectionStatus === "connected" ? (
            <Wifi className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-500" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-red-500" />
          )}
          <span className="hidden sm:inline text-sm text-muted-foreground capitalize">
            {connectionStatus}
          </span>
        </div>

        {/* Chat Status */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div
            className={`w-2 h-2 rounded-full ${getStatusColor(chatStatus)}`}
          />
          <span className="text-xs sm:text-sm text-muted-foreground">
            {getStatusText(chatStatus)}
          </span>
          {chatStatus === "streaming" && (
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          )}
        </div>

        {/* Queue Status Badge - Hidden on mobile */}
        {queueStatus && queueStatus.phase !== "finished" && (
          <Badge variant="secondary" className="hidden sm:inline-flex text-xs">
            Queue: {queueStatus.phase}
          </Badge>
        )}
      </div>

      {/* Right: Error or Queue Details */}
      <div className="flex items-center gap-2 ml-2">
        {/* Error Display - Truncated on mobile */}
        {error && (
          <div className="flex items-center gap-1.5 text-red-500 text-xs sm:text-sm max-w-[150px] sm:max-w-md">
            <AlertCircle className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
            <span className="truncate">{error.message}</span>
          </div>
        )}

        {/* Queue Details - Hidden on mobile */}
        {!error && queueStatus && queueStatus.phase !== "finished" && (
          <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
            <span>
              {queueStatus.inflight}/{queueStatus.maxParallel} active
            </span>
            {queueStatus.queued > 0 && (
              <span>• {queueStatus.queued} queued</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export const ChatStatusBar = memo(ChatStatusBarComponent);
