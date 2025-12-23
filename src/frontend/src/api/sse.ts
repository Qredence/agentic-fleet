/**
 * Chat SSE (Server-Sent Events) Client
 *
 * A typed SSE client for real-time chat streaming.
 * Replaces WebSocket with simpler, more robust SSE transport.
 *
 * Benefits over WebSocket:
 * - Built-in browser auto-reconnect
 * - Works through all proxies and CDNs
 * - Simpler error handling (standard HTTP errors)
 * - No persistent connection management
 * - Native keep-alive support
 */

import { getStreamApiBase } from "./config";
import { sseApi } from "./client";
import type { StreamEvent } from "./types";
import { StreamEventSchema } from "./validation";

// =============================================================================
// Types
// =============================================================================

export type SSEConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface ChatSSEOptions {
  /** Reasoning effort level: minimal, medium, maximal */
  reasoningEffort?: "minimal" | "medium" | "maximal";
  /** Enable workflow checkpointing */
  enableCheckpointing?: boolean;
}

export interface ChatSSECallbacks {
  /** Called when connection status changes */
  onStatusChange?: (status: SSEConnectionStatus) => void;
  /** Called when a stream event is received */
  onEvent?: (event: StreamEvent) => void;
  /** Called when the stream completes successfully */
  onComplete?: () => void;
  /** Called when an error occurs */
  onError?: (error: Error) => void;
}

// =============================================================================
// ChatSSEClient Class
// =============================================================================

export class ChatSSEClient {
  private eventSource: EventSource | null = null;
  private status: SSEConnectionStatus = "disconnected";
  private callbacks: ChatSSECallbacks = {};
  private currentWorkflowId: string | null = null;
  private currentConversationId: string | null = null;
  private currentUrl: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private lastHeartbeat: number = Date.now();
  private heartbeatTimeout = 30000; // 30 seconds without heartbeat = dead connection

  /**
   * Get current connection status.
   */
  get connectionStatus(): SSEConnectionStatus {
    return this.status;
  }

  /**
   * Check if connected and streaming.
   */
  get isConnected(): boolean {
    return this.eventSource !== null && this.status === "connected";
  }

  /**
   * Get the current workflow ID (available after connected event).
   */
  get workflowId(): string | null {
    return this.currentWorkflowId;
  }

  /**
   * Set event callbacks.
   */
  setCallbacks(callbacks: ChatSSECallbacks): void {
    this.callbacks = callbacks;
  }

  /**
   * Start streaming chat response.
   *
   * @param conversationId - The conversation ID
   * @param message - The user message
   * @param options - Optional streaming options
   */
  connect(
    conversationId: string,
    message: string,
    options: ChatSSEOptions = {},
  ): void {
    // Close any existing connection
    this.disconnect();

    this.currentConversationId = conversationId;
    this.setStatus("connecting");

    // Build SSE URL with query parameters
    const url = new URL(
      `${getStreamApiBase()}/chat/${conversationId}/stream`,
      window.location.origin,
    );
    url.searchParams.set("message", message);

    if (options.reasoningEffort) {
      url.searchParams.set("reasoning_effort", options.reasoningEffort);
    }
    if (options.enableCheckpointing) {
      url.searchParams.set("enable_checkpointing", "true");
    }

    // Store URL for reconnection attempts
    this.currentUrl = url.toString();

    // Create EventSource connection
    this.createEventSourceConnection(this.currentUrl);
  }

  /**
   * Create and attach event handlers to an EventSource.
   */
  private createEventSourceConnection(url: string): void {
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.setStatus("connected");
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000; // Reset delay on successful connection
      this.lastHeartbeat = Date.now();
      this.startHeartbeatCheck();
    };

    this.eventSource.onmessage = (event: MessageEvent) => {
      this.handleMessage(event.data);
      this.lastHeartbeat = Date.now(); // Update heartbeat on any message
    };

    this.eventSource.onerror = () => {
      const readyState = this.eventSource?.readyState;

      // EventSource.CONNECTING = 0, EventSource.OPEN = 1, EventSource.CLOSED = 2
      if (readyState === EventSource.CLOSED) {
        // Connection closed unexpectedly - surface error to caller and stop
        this.setStatus("error");
        this.callbacks.onError?.(
          new Error("SSE connection closed unexpectedly"),
        );
        // Cleanup resources for a closed connection
        this.cleanup();
      } else if (readyState === EventSource.CONNECTING) {
        // Still connecting - this is normal during initial connection
        // Don't treat as error yet
      } else {
        // Unknown state - treat as error
        this.setStatus("error");
      }
    };
  }

  /**
   * Handle incoming SSE message.
   */
  private handleMessage(data: string): void {
    try {
      // Handle empty or whitespace-only data
      if (!data || !data.trim()) {
        return;
      }

      const parsed = JSON.parse(data);

      // Guard against null or non-object parsed values
      if (!parsed || typeof parsed !== "object") {
        console.warn(
          "[SSE] Invalid event data: expected object, got",
          typeof parsed,
        );
        return;
      }

      // Validate event structure in development
      if (import.meta.env.DEV && StreamEventSchema) {
        try {
          const validation = StreamEventSchema.safeParse(parsed);
          if (!validation.success) {
            console.warn("[SSE] Invalid event structure:", validation.error);
          }
        } catch (validationErr) {
          // Catch any errors during validation (e.g., schema issues)
          console.warn("[SSE] Validation error:", validationErr);
        }
      }

      const event: StreamEvent = parsed;

      // Track workflow ID from connected event
      if (event.type === "connected" && event.data?.workflow_id) {
        this.currentWorkflowId = event.data.workflow_id as string;
      } else if (event.workflow_id) {
        this.currentWorkflowId = event.workflow_id;
      }

      // Handle heartbeat events
      if (event.type === "heartbeat") {
        this.lastHeartbeat = Date.now();
        return; // Don't emit heartbeat events to callbacks
      }

      // Emit event to callback
      this.callbacks.onEvent?.(event);

      // Handle terminal events
      if (event.type === "done") {
        this.callbacks.onComplete?.();
        this.disconnect();
      } else if (event.type === "error") {
        this.callbacks.onError?.(new Error(event.error || "Unknown error"));
      } else if (event.type === "cancelled") {
        this.callbacks.onComplete?.();
        this.disconnect();
      }
    } catch (err) {
      console.error("Failed to parse SSE event:", err, data);
      this.callbacks.onError?.(
        new Error(
          `Failed to parse SSE event: ${err instanceof Error ? err.message : "Unknown error"}`,
        ),
      );
    }
  }

  /**
   * Handle reconnection with exponential backoff.
   */
  private handleReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus("error");
      this.callbacks.onError?.(
        new Error(
          `Connection failed after ${this.maxReconnectAttempts} attempts. Please try again.`,
        ),
      );
      this.cleanup();
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      30000, // Max 30 seconds
    );

    this.setStatus("connecting");

    // Clear any existing timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      // EventSource will automatically attempt to reconnect
      // We just track the attempts and delay
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        // If still closed, try to reconnect manually
        this.attemptManualReconnect();
      }
    }, delay);
  }

  /**
   * Attempt manual reconnection by creating a new EventSource.
   */
  private attemptManualReconnect(): void {
    if (!this.currentUrl) {
      this.setStatus("error");
      this.callbacks.onError?.(
        new Error("Cannot reconnect: URL not available"),
      );
      return;
    }

    // Close existing EventSource if still open
    if (this.eventSource) {
      try {
        this.eventSource.close();
      } catch {
        // Ignore errors during close
      }
      this.eventSource = null;
    }

    // Set status to connecting before creating new connection
    this.setStatus("connecting");

    // Create new EventSource with same URL and reattach handlers
    this.createEventSourceConnection(this.currentUrl);
  }

  /**
   * Start heartbeat check to detect dead connections.
   */
  private startHeartbeatCheck(): void {
    this.stopHeartbeatCheck();

    this.heartbeatTimer = setInterval(() => {
      const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat;

      if (timeSinceLastHeartbeat > this.heartbeatTimeout) {
        console.warn("SSE heartbeat timeout - connection may be dead");
        this.setStatus("error");
        this.callbacks.onError?.(
          new Error("Connection timeout - no heartbeat received"),
        );
        this.stopHeartbeatCheck();
      }
    }, 5000); // Check every 5 seconds
  }

  /**
   * Stop heartbeat check.
   */
  private stopHeartbeatCheck(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Cancel the current stream.
   */
  async cancel(): Promise<void> {
    if (!this.currentConversationId || !this.currentWorkflowId) {
      return;
    }

    try {
      await sseApi.cancel(this.currentConversationId, this.currentWorkflowId);
    } catch (err) {
      console.error("Failed to cancel stream:", err);
    }

    this.disconnect();
  }

  /**
   * Submit a human-in-the-loop response.
   *
   * @param requestId - The request ID from the HITL event
   * @param response - The response payload
   */
  async submitResponse(requestId: string, response: unknown): Promise<void> {
    if (!this.currentConversationId || !this.currentWorkflowId) {
      throw new Error("No active stream to respond to");
    }

    await sseApi.submitResponse(
      this.currentConversationId,
      this.currentWorkflowId,
      requestId,
      response,
    );
  }

  /**
   * Disconnect and cleanup.
   */
  disconnect(): void {
    this.cleanup();
    this.setStatus("disconnected");
  }

  /**
   * Cleanup resources.
   */
  private cleanup(): void {
    this.stopHeartbeatCheck();

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.currentWorkflowId = null;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
  }

  /**
   * Update connection status and notify callback.
   */
  private setStatus(status: SSEConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.callbacks.onStatusChange?.(status);
    }
  }
}

// =============================================================================
// Singleton instance (matches WebSocket pattern for easy migration)
// =============================================================================

let sseClient: ChatSSEClient | null = null;

/**
 * Get or create the SSE client singleton.
 */
export function getSSEClient(): ChatSSEClient {
  if (!sseClient) {
    sseClient = new ChatSSEClient();
  }
  return sseClient;
}

/**
 * Reset the SSE client (for testing or cleanup).
 */
export function resetSSEClient(): void {
  if (sseClient) {
    sseClient.disconnect();
    sseClient = null;
  }
}

export default ChatSSEClient;
