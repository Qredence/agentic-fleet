/**
 * Native reconnecting WebSocket implementation.
 *
 * Replaces the unmaintained `reconnecting-websocket` package (last updated 2019)
 * with a lightweight native implementation supporting:
 * - Exponential backoff with configurable growth factor
 * - Maximum retry attempts
 * - Maximum reconnection delay cap
 * - Same event handler API as native WebSocket
 *
 * @see https://github.com/pladaria/reconnecting-websocket/issues/195
 */

export interface ReconnectingWebSocketOptions {
  /** Maximum number of reconnection attempts (default: 3) */
  maxRetries?: number;
  /** Initial reconnection delay in ms (default: 1000) */
  reconnectionDelay?: number;
  /** Delay multiplier for exponential backoff (default: 1.3) */
  reconnectionDelayGrowFactor?: number;
  /** Maximum reconnection delay cap in ms (default: 10000) */
  maxReconnectionDelay?: number;
}

type WebSocketEventHandler<K extends keyof WebSocketEventMap> = (
  event: WebSocketEventMap[K],
) => void;

/**
 * A WebSocket wrapper with automatic reconnection and exponential backoff.
 *
 * Usage:
 * ```ts
 * const ws = new ReconnectingWebSocket('ws://localhost:8000/api/ws/chat', {
 *   maxRetries: 3,
 *   reconnectionDelayGrowFactor: 1.3,
 * });
 *
 * ws.onopen = () => ws.send(JSON.stringify({ message: 'hello' }));
 * ws.onmessage = (e) => console.log(e.data);
 * ws.onerror = (e) => console.error(e);
 * ws.onclose = () => console.log('closed');
 * ```
 */
export class ReconnectingWebSocket {
  private url: string;
  private protocols?: string | string[];
  private options: Required<ReconnectingWebSocketOptions>;
  private ws: WebSocket | null = null;
  private retryCount = 0;
  private shouldReconnect = true;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  // Event handlers (same API as native WebSocket)
  public onopen: WebSocketEventHandler<"open"> | null = null;
  public onmessage: WebSocketEventHandler<"message"> | null = null;
  public onerror: WebSocketEventHandler<"error"> | null = null;
  public onclose: WebSocketEventHandler<"close"> | null = null;

  constructor(
    url: string,
    protocols?: string | string[],
    options: ReconnectingWebSocketOptions = {},
  ) {
    this.url = url;
    this.protocols = protocols;
    this.options = {
      maxRetries: options.maxRetries ?? 3,
      reconnectionDelay: options.reconnectionDelay ?? 1000,
      reconnectionDelayGrowFactor: options.reconnectionDelayGrowFactor ?? 1.3,
      maxReconnectionDelay: options.maxReconnectionDelay ?? 10000,
    };

    this.connect();
  }

  /** Current WebSocket ready state */
  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /** Whether the WebSocket is currently open */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Send data through the WebSocket.
   * @param data - Data to send (string, ArrayBuffer, Blob, or ArrayBufferView)
   */
  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      console.warn(
        "ReconnectingWebSocket: Cannot send, socket not open. ReadyState:",
        this.readyState,
      );
    }
  }

  /**
   * Close the WebSocket connection and stop reconnection attempts.
   * @param code - Optional close code (default: 1000)
   * @param reason - Optional close reason
   */
  close(code?: number, reason?: string): void {
    this.shouldReconnect = false;
    this.clearReconnectTimeout();
    if (this.ws) {
      this.ws.close(code ?? 1000, reason);
      this.ws = null;
    }
  }

  private connect(): void {
    if (!this.shouldReconnect) return;

    try {
      this.ws = this.protocols
        ? new WebSocket(this.url, this.protocols)
        : new WebSocket(this.url);

      this.ws.onopen = (event) => {
        this.retryCount = 0; // Reset retry count on successful connection
        this.onopen?.(event);
      };

      this.ws.onmessage = (event) => {
        this.onmessage?.(event);
      };

      this.ws.onerror = (event) => {
        this.onerror?.(event);
      };

      this.ws.onclose = (event) => {
        this.onclose?.(event);
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error("ReconnectingWebSocket: Connection error:", error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect) return;

    if (this.retryCount >= this.options.maxRetries) {
      console.warn(
        `ReconnectingWebSocket: Max retries (${this.options.maxRetries}) reached, giving up`,
      );
      return;
    }

    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.options.reconnectionDelay *
        Math.pow(this.options.reconnectionDelayGrowFactor, this.retryCount),
      this.options.maxReconnectionDelay,
    );

    this.retryCount++;
    console.log(
      `ReconnectingWebSocket: Reconnecting in ${Math.round(delay)}ms (attempt ${this.retryCount}/${this.options.maxRetries})`,
    );

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

export default ReconnectingWebSocket;
