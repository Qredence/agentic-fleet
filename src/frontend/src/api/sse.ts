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

import { API_BASE_URL } from "./config";
import type { StreamEvent } from "./types";

/**
 * Chat API prefix - uses /api (no version) for streaming endpoints.
 * This is intentionally different from API_PREFIX (/api/v1) used for REST endpoints.
 * The backend registers streaming routes at /api for frontend compatibility.
 */
const CHAT_API_PREFIX = "/api";

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
    const baseUrl = API_BASE_URL || "";
    const url = new URL(
      `${baseUrl}${CHAT_API_PREFIX}/chat/${conversationId}/stream`,
      window.location.origin,
    );
    url.searchParams.set("message", message);

    if (options.reasoningEffort) {
      url.searchParams.set("reasoning_effort", options.reasoningEffort);
    }
    if (options.enableCheckpointing) {
      url.searchParams.set("enable_checkpointing", "true");
    }

    // Create EventSource connection
    this.eventSource = new EventSource(url.toString());

    this.eventSource.onopen = () => {
      this.setStatus("connected");
    };

    this.eventSource.onmessage = (event: MessageEvent) => {
      this.handleMessage(event.data);
    };

    this.eventSource.onerror = () => {
      // EventSource auto-reconnects, but we track the error
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.setStatus("error");
        this.callbacks.onError?.(
          new Error("SSE connection closed unexpectedly"),
        );
        this.cleanup();
      }
    };
  }

  /**
   * Handle incoming SSE message.
   */
  private handleMessage(data: string): void {
    try {
      const event: StreamEvent = JSON.parse(data);

      // Track workflow ID from connected event
      if (event.type === "connected" && event.data?.workflow_id) {
        this.currentWorkflowId = event.data.workflow_id as string;
      } else if (event.workflow_id) {
        this.currentWorkflowId = event.workflow_id;
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
      // Use direct fetch to bypass /api/v1 prefix - streaming endpoints are at /api
      const baseUrl = API_BASE_URL || "";
      const url = `${baseUrl}${CHAT_API_PREFIX}/chat/${this.currentConversationId}/cancel?workflow_id=${this.currentWorkflowId}`;
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        throw new Error(
          `Cancel failed: ${response.status} ${response.statusText}`,
        );
      }
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

    // Use direct fetch to bypass /api/v1 prefix - streaming endpoints are at /api
    const baseUrl = API_BASE_URL || "";
    const url = `${baseUrl}${CHAT_API_PREFIX}/chat/${this.currentConversationId}/respond?workflow_id=${this.currentWorkflowId}`;
    const fetchResponse = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        response,
      }),
    });

    if (!fetchResponse.ok) {
      const errorText = await fetchResponse.text().catch(() => "Unknown error");
      throw new Error(
        `HITL response failed: ${fetchResponse.status} ${errorText}`,
      );
    }
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
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.currentWorkflowId = null;
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
