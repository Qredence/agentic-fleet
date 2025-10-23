/**
 * Robust SSE connection hook with automatic reconnection and error handling
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

interface SSEConnectionOptions {
  url: string;
  maxRetries?: number;
  retryDelay?: number;
  maxRetryDelay?: number;
  onMessage?: (event: MessageEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  headers?: Record<string, string>;
  autoConnect?: boolean;
  showToasts?: boolean;
}

interface SSEConnectionReturn {
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  connectionState: ConnectionState;
  retryCount: number;
  isConnected: boolean;
  lastError: string | null;
}

/**
 * Custom hook for managing SSE connections with robust error handling
 */
export function useSSEConnection({
  url,
  maxRetries = 5,
  retryDelay = 1000,
  maxRetryDelay = 30000,
  onMessage,
  onError,
  onOpen,
  onClose,
  headers = {},
  autoConnect = true,
  showToasts = true,
}: SSEConnectionOptions): SSEConnectionReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [retryCount, setRetryCount] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const isManualDisconnect = useRef(false);

  /**
   * Calculate retry delay with exponential backoff
   */
  const getRetryDelay = useCallback(
    (attempt: number): number => {
      const delay = retryDelay * Math.pow(2, attempt);
      return Math.min(delay, maxRetryDelay);
    },
    [retryDelay, maxRetryDelay]
  );

  /**
   * Clean up existing connection
   */
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  /**
   * Establish SSE connection
   */
  const connect = useCallback(() => {
    // Clean up existing connection
    cleanup();

    isManualDisconnect.current = false;
    setConnectionState("connecting");
    setLastError(null);

    try {
      // Append headers as query parameters (SSE limitation)
      const params = new URLSearchParams(headers);
      const fullUrl = `${url}${params.toString() ? (url.includes('?') ? '&' : '?') + params.toString() : ""}`;

      const eventSource = new EventSource(fullUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setConnectionState("connected");
        setRetryCount(0);
        setLastError(null);

        if (showToasts) {
          toast.success("Connected to server", { duration: 2000 });
        }

        onOpen?.();
      };

      eventSource.onmessage = (event) => {
        try {
          onMessage?.(event);
        } catch (error) {
          console.error("Error handling SSE message:", error);
          const errorMessage = error instanceof Error ? error.message : "Unknown error";
          setLastError(errorMessage);

          if (showToasts) {
            toast.error(`Message handling error: ${errorMessage}`);
          }
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE connection error:", error);
        setConnectionState("error");

        const errorMessage = "Connection error occurred";
        setLastError(errorMessage);

        onError?.(error);

        // Only attempt reconnection if not manually disconnected
        if (!isManualDisconnect.current && retryCount < maxRetries) {
          const delay = getRetryDelay(retryCount);

          if (showToasts) {
            toast.warning(
              `Connection lost. Retrying in ${(delay / 1000).toFixed(0)}s... (${retryCount + 1}/${maxRetries})`,
              { duration: delay }
            );
          }

          reconnectTimeoutRef.current = setTimeout(() => {
            setRetryCount((prev) => prev + 1);
          }, delay);
        } else if (retryCount >= maxRetries) {
          setConnectionState("disconnected");

          if (showToasts) {
            toast.error("Unable to connect to server. Please refresh the page.", {
              duration: 5000,
            });
          }

          cleanup();
        }
      };
    } catch (error) {
      console.error("Failed to create EventSource:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setLastError(errorMessage);
      setConnectionState("error");

      if (showToasts) {
        toast.error(`Connection failed: ${errorMessage}`);
      }
    }
  }, [
    url,
    headers,
    maxRetries,
    retryCount,
    getRetryDelay,
    cleanup,
    onMessage,
    onError,
    onOpen,
    showToasts,
  ]);

  /**
   * Disconnect from SSE
   */
  const disconnect = useCallback(() => {
    isManualDisconnect.current = true;
    cleanup();
    setConnectionState("disconnected");
    setRetryCount(0);
    setLastError(null);
    onClose?.();
  }, [cleanup, onClose]);

  /**
   * Force reconnection (resets retry count)
   */
  const reconnect = useCallback(() => {
    setRetryCount(0);
    connect();
  }, [connect]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      isManualDisconnect.current = true;
      cleanup();
    };
  }, [autoConnect, connect, cleanup]);

  // Handle visibility change (pause/resume connection)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page hidden, could pause reconnection attempts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
      } else {
        // Page visible again, reconnect if disconnected and not already connecting
        if (
          connectionState === "disconnected" &&
          !isManualDisconnect.current &&
          connectionState !== "connecting"
        ) {
          reconnect();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [connectionState, reconnect, cleanup]);

  return {
    connect,
    disconnect,
    reconnect,
    connectionState,
    retryCount,
    isConnected: connectionState === "connected",
    lastError,
  };
}
