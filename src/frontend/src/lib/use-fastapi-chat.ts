/**
 * useFastAPIChat Hook - Main Orchestrator
 *
 * Composes 4 specialized hooks:
 * - useMessageState: Message accumulation and streaming
 * - useApprovalWorkflow: Human-in-the-loop approval requests
 * - useConversationHistory: Load & parse conversation history
 *
 * Remaining responsibilities:
 * - Chat submission (sendMessage)
 * - SSE event coordination
 * - Connection health checks
 * - Chat UI state (input, status, error, plan)
 *
 * Note: SSE Event types are defined in hooks/useSSEConnection.ts
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { API_ENDPOINTS, buildApiUrl } from "./api-config";
import {
  useApprovalWorkflow,
  type ApprovalActionState,
  type ApprovalResponsePayload,
  type PendingApproval,
} from "./hooks/useApprovalWorkflow";
import { useConversationHistory } from "./hooks/useConversationHistory";
import { useMessageState, type Message } from "./hooks/useMessageState";
import { type SSEEvent } from "./hooks/useSSEConnection";

// ============================================================================
// Retry Logic & Utilities
// ============================================================================

/**
 * Retry configuration for API calls
 */
const RETRY_CONFIG = {
  maxAttempts: 3,
  initialDelayMs: 100,
  maxDelayMs: 1000,
  backoffMultiplier: 2,
};

/**
 * Calculate exponential backoff delay
 */
const calculateBackoffDelay = (attempt: number): number => {
  const delay = RETRY_CONFIG.initialDelayMs * Math.pow(RETRY_CONFIG.backoffMultiplier, attempt);
  return Math.min(delay, RETRY_CONFIG.maxDelayMs);
};

/**
 * Retry a fetch operation with exponential backoff
 */
const fetchWithRetry = async (
  url: string,
  options: RequestInit & { signal?: AbortSignal },
  maxAttempts = RETRY_CONFIG.maxAttempts
): Promise<Response> => {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const response = await fetch(url, options);

      // Don't retry on client errors (4xx), only on server errors (5xx) and network errors
      if (!response.ok && response.status < 500) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Don't retry if we have an AbortSignal that's been aborted
      if (options.signal?.aborted) {
        throw lastError;
      }

      // If this is the last attempt, throw the error
      if (attempt === maxAttempts - 1) {
        throw lastError;
      }

      // Wait before retrying with exponential backoff
      const delay = calculateBackoffDelay(attempt);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error("Unknown error during retry");
};

/**
 * Create a new conversation on the backend
 */
const createConversation = async (): Promise<string> => {
  const response = await fetchWithRetry(buildApiUrl(API_ENDPOINTS.CONVERSATIONS), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as { id: string };
  return data.id;
};

// ============================================================================
// Types & Exports
// ============================================================================

// Re-export message types from useMessageState for consuming components
export type { Message, ToolCall } from "./hooks/useMessageState";

// Re-export approval types from useApprovalWorkflow for consuming components
export type {
  ApprovalActionState,
  ApprovalResponsePayload,
  PendingApproval,
} from "./hooks/useApprovalWorkflow";

// Chat state types
export type ChatStatus = "ready" | "submitted" | "streaming" | "error";

export type ConnectionStatus = "connected" | "disconnected" | "connecting";

export type QueuePhase = "queued" | "started" | "finished" | string;

export interface QueueStatus {
  phase: QueuePhase;
  inflight: number;
  queued: number;
  maxParallel: number;
}

// Hook configuration and return types
export interface UseFastAPIChatOptions {
  /** Model/entity ID to use (default: 'magentic_fleet') */
  model?: string;
  /** Conversation ID for context */
  conversationId?: string;
}

export interface Plan {
  id: string;
  title: string;
  description?: string;
  steps: string[];
  isStreaming: boolean;
}

export interface UseFastAPIChatReturn {
  // Message management (from useMessageState)
  messages: Message[];

  // User input
  input: string;
  setInput: (value: string) => void;

  // Chat submission
  sendMessage: (content: string) => Promise<void>;

  // Chat status
  status: ChatStatus;
  error: Error | null;
  currentPlan: Plan | null;
  queueStatus: QueueStatus | null;

  // Approval workflow (from useApprovalWorkflow)
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  respondToApproval: (requestId: string, payload: ApprovalResponsePayload) => Promise<void>;
  refreshApprovals: () => Promise<void>;

  // Connection status (health checks)
  connectionStatus: ConnectionStatus;
  checkHealth: () => Promise<void>;

  // Conversation context
  conversationId?: string;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useFastAPIChat({
  model = "magentic_fleet",
  conversationId: initialConversationId,
}: UseFastAPIChatOptions = {}): UseFastAPIChatReturn {
  // ══════════════════════════════════════════════════════════════════════════
  // Composed Hooks
  // ══════════════════════════════════════════════════════════════════════════
  const messageState = useMessageState();
  const approvalWorkflow = useApprovalWorkflow();
  const conversationHistory = useConversationHistory();

  // ══════════════════════════════════════════════════════════════════════════
  // UI State
  // ══════════════════════════════════════════════════════════════════════════
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<Error | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(initialConversationId);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");

  // ══════════════════════════════════════════════════════════════════════════
  // Refs
  // ══════════════════════════════════════════════════════════════════════════
  const healthCheckIntervalRef = useRef<number | null>(null);
  const retryCountRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastLoadedConversationRef = useRef<string | undefined>(undefined);

  // ══════════════════════════════════════════════════════════════════════════
  // Connection Health Checks
  // ══════════════════════════════════════════════════════════════════════════
  /**
   * Check backend health and update connection status
   * Implements exponential backoff for retries
   */
  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout

      const response = await fetch(buildApiUrl(API_ENDPOINTS.HEALTH), {
        method: "HEAD",
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        setConnectionStatus("connected");
        retryCountRef.current = 0; // Reset retry count on success
      } else {
        setConnectionStatus("disconnected");
      }
    } catch (err) {
      setConnectionStatus("disconnected");

      // Increment retry count for exponential backoff
      retryCountRef.current += 1;

      // Log only if not a typical connection refused error
      if (err instanceof Error && !err.message.includes("Failed to fetch")) {
        console.warn("Health check failed:", err.message);
      }
    }
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // SSE Event Handling & Chat Submission
  // ══════════════════════════════════════════════════════════════════════════

  /**
   * Handle individual SSE events from the backend
   */
  const handleSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "response.output_text.delta": {
          if (!messageState.currentMessageId) {
            messageState.startStreamingMessage(event.item_id, event.delta, event.actor);
          } else {
            messageState.appendDelta(event.delta);
          }
          break;
        }

        case "workflow.event": {
          const textLower = event.text.toLowerCase();
          const isPlanIndicator =
            event.actor?.toLowerCase().includes("plan") ||
            event.actor?.toLowerCase().includes("manager") ||
            event.actor?.toLowerCase().includes("orchestrat") ||
            textLower.includes("plan:") ||
            textLower.includes("planning");

          if (isPlanIndicator && event.text.includes(":")) {
            const lines = event.text.split("\n").filter((l) => l.trim());
            const planTitle = lines[0]?.replace(/.*plan:?/i, "").trim() || "Execution Plan";
            const planSteps = lines.slice(1).filter((l) => l.trim());

            if (planSteps.length > 0) {
              setCurrentPlan({
                id: event.message_id,
                title: planTitle,
                description: undefined,
                steps: planSteps,
                isStreaming: true,
              });
            }
          }

          const workerPattern = /(Worker:\s*[^\n]+)/g;
          const workerMatches = event.text.match(workerPattern);

          if (workerMatches && workerMatches.length > 0) {
            workerMatches.forEach((workerText, index) => {
              const cleanedText = workerText.replace(/^Worker:\s*/, "");
              const systemMessage: Message = {
                id: `${event.message_id}-worker-${index}`,
                role: "system",
                content: cleanedText,
                actor: event.actor || "Worker",
                isNew: true,
              };
              messageState.addMessage(systemMessage);
            });
          } else {
            const systemMessage: Message = {
              id: event.message_id,
              role: "system",
              content: event.text,
              actor: event.actor,
              isNew: true,
            };
            messageState.addMessage(systemMessage);
          }
          break;
        }

        case "response.completed": {
          messageState.finishStreaming();
          setCurrentPlan((prev) => (prev ? { ...prev, isStreaming: false } : null));
          const responseConvId = event.response.conversation_id;
          if (responseConvId) {
            setConversationId(responseConvId);
          }
          setQueueStatus(null);
          approvalWorkflow.fetchApprovals();
          break;
        }

        case "response.function_approval.requested": {
          approvalWorkflow.handleApprovalRequested(event);
          break;
        }

        case "response.function_approval.responded": {
          approvalWorkflow.handleApprovalResponded(event);
          break;
        }

        case "response.queue_status": {
          const metrics = event.metrics || {};
          setQueueStatus({
            phase: (metrics.phase as QueuePhase) || "queued",
            inflight: Number(metrics.inflight ?? 0),
            queued: Number(metrics.queued ?? 0),
            maxParallel: Number(metrics.max_parallel ?? 0),
          });
          break;
        }

        case "error": {
          const errorMessage = event.error?.message || event.message || "An error occurred";
          setError(new Error(errorMessage));
          setStatus("error");
          setQueueStatus(null);
          break;
        }

        default:
          console.warn("Unknown SSE event type:", (event as { type?: string }).type);
      }
    },
    [messageState, approvalWorkflow]
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Conversation History Loading
  // ══════════════════════════════════════════════════════════════════════════

  const loadConversationHistory = useCallback(
    async (conversation: string) => {
      const messages = await conversationHistory.loadHistory(conversation);
      messageState.setMessages(messages);
      messageState.resetStreaming();
    },
    [conversationHistory, messageState]
  );

  /**
   * Send a message to the FastAPI backend and handle SSE streaming
   * Now with explicit conversation creation and improved error handling
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (status === "streaming" || status === "submitted") {
        return; // Prevent duplicate submissions
      }

      setStatus("submitted");
      setError(null);
      setCurrentPlan(null); // Reset plan for new message

      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
      };
      messageState.addMessage(userMessage);

      // Reset streaming state for new response
      messageState.resetStreaming();

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        // Ensure we have a conversation ID (create one if needed)
        let activeConversationId = conversationId;
        if (!activeConversationId) {
          try {
            activeConversationId = await createConversation();
            setConversationId(activeConversationId);
          } catch (error) {
            const errorMsg =
              error instanceof Error ? error.message : "Failed to create conversation";
            setError(new Error(`Conversation creation failed: ${errorMsg}`));
            setStatus("error");
            return;
          }
        }

        const payload = {
          model,
          conversation: activeConversationId,
          input: [
            {
              type: "message",
              role: "user",
              content: [
                {
                  type: "input_text",
                  text: content,
                },
              ],
            },
          ],
        };

        // Use retry logic for the initial POST request
        let response: Response;
        try {
          response = await fetchWithRetry(buildApiUrl(API_ENDPOINTS.RESPONSES), {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
            signal: controller.signal,
          });
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : "Request failed";
          setError(new Error(`Failed to send message: ${errorMsg}`));
          setStatus("error");
          return;
        }

        if (!response.body) {
          throw new Error("Response body is null");
        }

        setStatus("streaming");

        // Parse SSE stream with improved error handling
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let eventBuffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              // Process any remaining data in eventBuffer
              if (eventBuffer.trim()) {
                try {
                  const event: SSEEvent = JSON.parse(eventBuffer);
                  handleSSEEvent(event);
                } catch (e) {
                  console.warn("Failed to parse final SSE event:", e, eventBuffer);
                }
              }
              break;
            }

            buffer += decoder.decode(value, { stream: true });

            // Handle SSE events which may contain embedded newlines
            // SSE format: "data: {json}\n\n"
            const parts = buffer.split("\n\n");

            // Keep the last part (may be incomplete)
            buffer = parts.pop() || "";

            // Process complete events
            for (const part of parts) {
              const lines = part.split("\n");
              for (const line of lines) {
                if (!line.trim() || line.startsWith(":")) {
                  // Skip empty lines and comments (heartbeats)
                  continue;
                }

                if (line.startsWith("data: ")) {
                  const data = line.slice(6);

                  if (data === "[DONE]") {
                    setStatus("ready");
                    continue;
                  }

                  // Accumulate potential multi-line JSON
                  eventBuffer += data;

                  try {
                    const event: SSEEvent = JSON.parse(eventBuffer);
                    handleSSEEvent(event);
                    eventBuffer = "";
                  } catch (parseError) {
                    // JSON might be incomplete, wait for more data
                    // Only log if we have accumulated a lot of data (likely malformed)
                    if (eventBuffer.length > 10000) {
                      console.error(
                        "SSE event buffer exceeded limit, discarding:",
                        eventBuffer.substring(0, 100),
                        parseError
                      );
                      eventBuffer = "";
                    }
                  }
                }
              }
            }
          }

          // Ensure status is set to ready if still streaming
          setStatus((prev) => (prev === "streaming" ? "ready" : prev));
        } catch (streamError) {
          if (controller.signal.aborted) {
            setStatus("error");
            setError(new Error("Request aborted"));
          } else {
            const errorMsg =
              streamError instanceof Error ? streamError.message : "Stream processing failed";
            setError(new Error(`Stream error: ${errorMsg}`));
            setStatus("error");
          }
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Unknown error";
        setError(new Error(errorMsg));
        setStatus("error");
      } finally {
        abortControllerRef.current = null;
      }
    },
    [status, model, conversationId, messageState, handleSSEEvent]
  );

  // Cleanup on unmount - abort any ongoing SSE connections
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    if (initialConversationId) {
      // Only load if conversation ID actually changed
      if (
        initialConversationId !== conversationId ||
        lastLoadedConversationRef.current !== initialConversationId
      ) {
        setConversationId(initialConversationId);
        lastLoadedConversationRef.current = initialConversationId;
        loadConversationHistory(initialConversationId);
      }
    } else if (!initialConversationId && conversationId) {
      setConversationId(undefined);
      lastLoadedConversationRef.current = undefined;
      messageState.clearMessages();
      approvalWorkflow.clearApprovals();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialConversationId]);

  // ══════════════════════════════════════════════════════════════════════════
  // Approval Response Handler
  // ══════════════════════════════════════════════════════════════════════════

  /**
   * Respond to a pending approval request
   * Delegates to approvalWorkflow hook
   */
  const respondToApproval = useCallback(
    async (requestId: string, action: ApprovalResponsePayload) => {
      return approvalWorkflow.respondToApproval(requestId, action);
    },
    [approvalWorkflow]
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Effects
  // ══════════════════════════════════════════════════════════════════════════

  // Health check polling with exponential backoff
  useEffect(() => {
    // Check immediately on mount
    checkHealth();

    // Clear any existing timeout
    if (healthCheckIntervalRef.current !== null) {
      clearTimeout(healthCheckIntervalRef.current);
      healthCheckIntervalRef.current = null;
    }

    // Only schedule recurring checks when disconnected
    if (connectionStatus === "disconnected") {
      // Base delay: 5s, max delay: 60s, backoff multiplier: 1.5
      const baseDelay = 5000; // 5 seconds
      const maxDelay = 60000; // 60 seconds
      const backoffMultiplier = 1.5;
      const delay = Math.min(
        baseDelay * Math.pow(backoffMultiplier, retryCountRef.current),
        maxDelay
      );

      healthCheckIntervalRef.current = window.setTimeout(() => {
        checkHealth();
      }, delay);
    }

    return () => {
      if (healthCheckIntervalRef.current !== null) {
        clearTimeout(healthCheckIntervalRef.current);
      }
    };
  }, [connectionStatus, checkHealth]); // Re-run when connection status changes

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (healthCheckIntervalRef.current !== null) {
        clearTimeout(healthCheckIntervalRef.current);
      }
    };
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // Return Value - Composed Hook API
  // ══════════════════════════════════════════════════════════════════════════

  return {
    // Message management (from useMessageState)
    messages: messageState.messages,

    // User input
    input,
    setInput,

    // Chat submission and status
    sendMessage,
    status,
    error,
    currentPlan,
    queueStatus,

    // Approval workflow (from useApprovalWorkflow)
    pendingApprovals: approvalWorkflow.pendingApprovals,
    approvalStatuses: approvalWorkflow.approvalStatuses,
    respondToApproval,
    refreshApprovals: approvalWorkflow.fetchApprovals,

    // Connection status
    connectionStatus,
    checkHealth,

    // Conversation context
    conversationId,
  };
}
