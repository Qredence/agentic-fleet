import { useCallback, useEffect, useRef, useState } from "react";

export interface WebSocketMessage {
  type: string;
  data: Record<string, unknown>;
}

interface UseWebSocketOptions {
  url: string | null;
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  reconnect?: boolean;
  reconnectIntervalMs?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  sendJson: (payload: Record<string, unknown>) => void;
  close: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect = true,
    reconnectIntervalMs = 2_000,
  } = options;

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number>();
  const [isConnected, setIsConnected] = useState(false);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== undefined) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = undefined;
    }
  }, []);

  const cleanupSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onmessage = null;
      socketRef.current.onerror = null;
      socketRef.current.onclose = null;
      try {
        socketRef.current.close();
      } catch (error) {
        console.warn("Error closing WebSocket", error);
      }
      socketRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (!url) {
      cleanupSocket();
      return undefined;
    }

    let isCancelled = false;

    const connect = () => {
      if (!url || isCancelled) {
        return;
      }

      try {
        const socket = new WebSocket(url);
        socketRef.current = socket;

        socket.onopen = (event) => {
          setIsConnected(true);
          clearReconnectTimer();
          onOpen?.(event);
        };

        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload && typeof payload.type === "string") {
              onMessage?.({
                type: payload.type,
                data: (payload.data ?? {}) as Record<string, unknown>,
              });
            }
          } catch (err) {
            console.error("Failed to parse WebSocket message", err);
          }
        };

        socket.onerror = (event) => {
          onError?.(event);
        };

        socket.onclose = (event) => {
          setIsConnected(false);
          onClose?.(event);
          if (reconnect && !isCancelled) {
            clearReconnectTimer();
            reconnectTimerRef.current = window.setTimeout(connect, reconnectIntervalMs);
          }
        };
      } catch (error) {
        console.error("Failed to create WebSocket", error);
        if (reconnect && !isCancelled) {
          clearReconnectTimer();
          reconnectTimerRef.current = window.setTimeout(connect, reconnectIntervalMs);
        }
      }
    };

    connect();

    return () => {
      isCancelled = true;
      clearReconnectTimer();
      cleanupSocket();
    };
  }, [
    url,
    reconnect,
    reconnectIntervalMs,
    onMessage,
    onOpen,
    onClose,
    onError,
    cleanupSocket,
    clearReconnectTimer,
  ]);

  const sendJson = useCallback((payload: Record<string, unknown>) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      console.warn("Attempted to send on closed WebSocket connection");
      return;
    }

    socketRef.current.send(JSON.stringify(payload));
  }, []);

  const close = useCallback(() => {
    clearReconnectTimer();
    cleanupSocket();
  }, [cleanupSocket, clearReconnectTimer]);

  return {
    isConnected,
    sendJson,
    close,
  };
}
