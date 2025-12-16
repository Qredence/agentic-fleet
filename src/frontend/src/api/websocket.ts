/**
 * Chat WebSocket Service
 *
 * A typed WebSocket service for real-time chat streaming.
 * Handles connection management, message queuing, heartbeat, and reconnection.
 */

import { getWebSocketUrl } from "./config";
import type {
  StreamEvent,
  ChatRequest,
  CancelRequest,
  WebSocketClientMessage,
  WorkflowResponseRequest,
  WorkflowResumeRequest,
} from "./types";

// =============================================================================
// Types
// =============================================================================

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface ChatWebSocketOptions {
  /** Maximum reconnection attempts (default: 3) */
  maxRetries?: number;
  /** Initial reconnection delay in ms (default: 1000) */
  reconnectionDelay?: number;
  /** Delay multiplier for exponential backoff (default: 1.5) */
  reconnectionDelayGrowFactor?: number;
  /** Maximum reconnection delay cap in ms (default: 10000) */
  maxReconnectionDelay?: number;
  /** Heartbeat interval in ms (default: 25000) */
  heartbeatInterval?: number;
  /** Connection timeout in ms (default: 15000) */
  connectionTimeout?: number;
}

export interface ChatWebSocketCallbacks {
  /** Called when connection status changes */
  onStatusChange?: (status: ConnectionStatus) => void;
  /** Called when a stream event is received */
  onEvent?: (event: StreamEvent) => void;
  /** Called when the stream completes */
  onComplete?: () => void;
  /** Called when an error occurs */
  onError?: (error: Error) => void;
}

// =============================================================================
// ChatWebSocketService Class
// =============================================================================

export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private options: Required<ChatWebSocketOptions>;
  private callbacks: ChatWebSocketCallbacks = {};
  private retryCount = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private connectionTimeout: ReturnType<typeof setTimeout> | null = null;
  private status: ConnectionStatus = "disconnected";
  private messageQueue: string[] = [];
  private pendingRequest: ChatRequest | WorkflowResumeRequest | null = null;
  private shouldReconnect = false;

  constructor(options: ChatWebSocketOptions = {}) {
    this.options = {
      maxRetries: options.maxRetries ?? 3,
      reconnectionDelay: options.reconnectionDelay ?? 1000,
      reconnectionDelayGrowFactor: options.reconnectionDelayGrowFactor ?? 1.5,
      maxReconnectionDelay: options.maxReconnectionDelay ?? 10000,
      heartbeatInterval: options.heartbeatInterval ?? 25000,
      connectionTimeout: options.connectionTimeout ?? 15000,
    };
  }

  /**
   * Get current connection status.
   */
  get connectionStatus(): ConnectionStatus {
    return this.status;
  }

  /**
   * Check if connected and ready.
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Set event callbacks.
   */
  setCallbacks(callbacks: ChatWebSocketCallbacks): void {
    this.callbacks = callbacks;
  }

  /**
   * Connect and send a chat request.
   * Creates a new WebSocket connection and sends the request.
   */
  connect(request: ChatRequest | WorkflowResumeRequest): void {
    // Close any existing connection
    this.disconnect();

    this.pendingRequest = request;
    this.shouldReconnect = true;
    this.retryCount = 0;

    this.createConnection();
  }

  /**
   * Send an arbitrary client message over the WebSocket.
   * If the socket isn't open yet, the message will be queued and flushed on connect.
   */
  send(message: WebSocketClientMessage): void {
    const payload = JSON.stringify(message);

    if (this.isConnected) {
      this.ws?.send(payload);
      return;
    }

    this.messageQueue.push(payload);
  }

  /**
   * Send a workflow response for a pending HITL request.
   */
  sendWorkflowResponse(requestId: string, response: unknown): void {
    const msg: WorkflowResponseRequest = {
      type: "workflow.response",
      request_id: requestId,
      response,
    };
    this.send(msg);
  }

  /**
   * Send a cancel request to abort the current stream.
   */
  cancel(): void {
    if (this.isConnected) {
      const cancelRequest: CancelRequest = { type: "cancel" };
      this.ws?.send(JSON.stringify(cancelRequest));
      // Give browser time to flush the send buffer
      setTimeout(() => {
        this.shouldReconnect = false;
        this.disconnect();
      }, 50);
      return;
    }
    this.shouldReconnect = false;
    this.disconnect();
  }

  /**
   * Disconnect and cleanup.
   */
  disconnect(): void {
    this.shouldReconnect = false;
    this.clearTimeouts();

    if (this.ws) {
      // Remove listeners before closing to prevent callbacks
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;

      if (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ) {
        this.ws.close(1000, "Client disconnect");
      }
      this.ws = null;
    }

    this.messageQueue = [];
    this.pendingRequest = null;
    this.setStatus("disconnected");
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private createConnection(): void {
    if (this.ws) {
      return;
    }

    this.setStatus("connecting");

    const wsUrl = getWebSocketUrl("/api/ws/chat");

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
      this.startConnectionTimeout();
    } catch (error) {
      console.error("WebSocket creation failed:", error);
      this.handleConnectionError(
        error instanceof Error ? error : new Error("Connection failed"),
      );
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.clearConnectionTimeout();
      this.setStatus("connected");
      this.retryCount = 0;

      // Send pending request
      if (this.pendingRequest) {
        this.ws?.send(JSON.stringify(this.pendingRequest));
      }

      // Flush message queue
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        if (msg && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(msg);
        }
      }

      this.startHeartbeatTimer();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.resetHeartbeatTimer();

      try {
        const data: StreamEvent = JSON.parse(event.data as string);

        // Handle heartbeat internally
        if (data.type === "heartbeat") {
          return;
        }

        // Emit event to callback
        this.callbacks.onEvent?.(data);

        // Handle terminal events
        if (data.type === "done" || data.type === "cancelled") {
          this.shouldReconnect = false;
          this.callbacks.onComplete?.();
          // Let server close the connection
        }

        // Handle errors
        if (data.type === "error") {
          this.callbacks.onError?.(new Error(data.error || "Stream error"));
        }
      } catch (e) {
        console.error("Error parsing WebSocket message:", e);
      }
    };

    this.ws.onerror = (event) => {
      console.error("WebSocket error:", event);
      this.setStatus("error");
    };

    this.ws.onclose = (event) => {
      this.clearTimeouts();
      this.ws = null;

      // Only attempt reconnect if it was unexpected
      if (this.shouldReconnect && event.code !== 1000) {
        this.scheduleReconnect();
      } else {
        this.setStatus("disconnected");
      }
    };
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.retryCount >= this.options.maxRetries) {
      console.warn(
        `WebSocket: Max retries (${this.options.maxRetries}) reached`,
      );
      this.setStatus("error");
      this.callbacks.onError?.(
        new Error("Connection failed after max retries"),
      );
      return;
    }

    const delay = Math.min(
      this.options.reconnectionDelay *
        Math.pow(this.options.reconnectionDelayGrowFactor, this.retryCount),
      this.options.maxReconnectionDelay,
    );

    this.retryCount++;
    console.log(
      `WebSocket: Reconnecting in ${Math.round(delay)}ms (attempt ${this.retryCount})`,
    );

    this.reconnectTimeout = setTimeout(() => {
      this.createConnection();
    }, delay);
  }

  private handleConnectionError(error: Error): void {
    this.setStatus("error");
    this.callbacks.onError?.(error);

    if (this.shouldReconnect) {
      this.scheduleReconnect();
    }
  }

  private setStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.callbacks.onStatusChange?.(status);
    }
  }

  private startConnectionTimeout(): void {
    this.clearConnectionTimeout();
    this.connectionTimeout = setTimeout(() => {
      if (this.ws?.readyState !== WebSocket.OPEN) {
        console.warn("WebSocket: Connection timeout");
        this.ws?.close();
        this.handleConnectionError(new Error("Connection timeout"));
      }
    }, this.options.connectionTimeout);
  }

  private clearConnectionTimeout(): void {
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
  }

  private startHeartbeatTimer(): void {
    this.clearHeartbeatTimer();
    this.heartbeatTimeout = setTimeout(() => {
      // If we haven't received anything in heartbeatInterval, connection may be dead
      console.warn(
        "WebSocket: Heartbeat timeout, closing connection to trigger recovery",
      );
      if (
        this.ws &&
        (this.ws.readyState === WebSocket.OPEN ||
          this.ws.readyState === WebSocket.CONNECTING)
      ) {
        this.ws.close(4000, "Heartbeat timeout"); // Custom code 4000 for heartbeat timeout
      }
    }, this.options.heartbeatInterval + 10000); // Give extra buffer
  }

  private resetHeartbeatTimer(): void {
    this.startHeartbeatTimer();
  }

  private clearHeartbeatTimer(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private clearTimeouts(): void {
    this.clearConnectionTimeout();
    this.clearHeartbeatTimer();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

let chatWebSocketInstance: ChatWebSocketService | null = null;

/**
 * Get the singleton ChatWebSocketService instance.
 */
export function getChatWebSocket(): ChatWebSocketService {
  if (!chatWebSocketInstance) {
    chatWebSocketInstance = new ChatWebSocketService();
  }
  return chatWebSocketInstance;
}

/**
 * Create a new ChatWebSocketService instance with custom options.
 */
export function createChatWebSocket(
  options?: ChatWebSocketOptions,
): ChatWebSocketService {
  return new ChatWebSocketService(options);
}
