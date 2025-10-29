/**
 * ChatStatusBar Component
 *
 * Displays status information about the chat session:
 * - Connection status indicator
 * - Current chat status
 * - Error messages
 * - Queue status information
 */

import { memo } from "react";
import { Badge } from "@/components/ui/shadcn/badge";
import { AlertCircle, Loader2, Wifi, WifiOff } from "lucide-react";
import type { ConnectionStatus, ChatStatus, QueueStatus } from "@/lib/hooks/useChatState";

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
    <div className={`flex items-center justify-between px-4 py-2 border-t bg-background ${className}`}>
      <div className="flex items-center gap-3">
        {/* Connection Status */}
        <div className="flex items-center gap-2">
          {connectionStatus === "connected" ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-500" />
          )}
          <span className="text-sm text-muted-foreground capitalize">
            {connectionStatus}
          </span>
        </div>

        {/* Chat Status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${getStatusColor(chatStatus)}`} />
          <span className="text-sm text-muted-foreground">
            {getStatusText(chatStatus)}
          </span>
          {chatStatus === "streaming" && (
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          )}
        </div>

        {/* Queue Status */}
        {queueStatus && queueStatus.phase !== "finished" && (
          <Badge variant="secondary" className="text-xs">
            Queue: {queueStatus.phase}
          </Badge>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm max-w-md">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="truncate">{error.message}</span>
        </div>
      )}

      {/* Queue Details */}
      {queueStatus && queueStatus.phase !== "finished" && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{queueStatus.inflight}/{queueStatus.maxParallel} active</span>
          {queueStatus.queued > 0 && (
            <span>• {queueStatus.queued} queued</span>
          )}
        </div>
      )}
    </div>
  );
};

export const ChatStatusBar = memo(ChatStatusBarComponent);
