/**
 * useFastAPIChat Hook - Consolidated Implementation
 *
 * A simplified, working implementation that provides all the functionality
 * needed for the chat interface. This consolidates message management,
 * SSE streaming, approvals, and connection health in a single hook.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket, type WebSocketMessage } from "./hooks/useWebSocket";
import type {
  ApprovalActionState,
  ApprovalResponsePayload,
  ChatStatus,
  ConnectionStatus,
  Message,
  PendingApproval,
  Plan,
  QueueStatus,
} from "./types";

// Re-export types for consuming components
export type {
  ApprovalActionState,
  ApprovalResponsePayload,
  ChatStatus,
  ConnectionStatus,
  Message,
  PendingApproval,
  Plan,
  QueueStatus,
  ToolCall,
  WorkflowEventType,
} from "./types";

// ══════════════════════════════════════════════════════════════════════════
// Hook Options and Return Type
// ══════════════════════════════════════════════════════════════════════════

export interface UseFastAPIChatOptions {
  /** Model/entity ID to use (default: 'dynamic_orchestration') */
  model?: string;
  /** Conversation ID for context */
  conversationId?: string;
}

export interface UseFastAPIChatReturn {
  // Message management
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

  // Approval workflow
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  respondToApproval: (requestId: string, payload: ApprovalResponsePayload) => Promise<void>;
  refreshApprovals: () => Promise<void>;

  // Connection status
  connectionStatus: ConnectionStatus;
  checkHealth: () => Promise<void>;

  // Conversation context
  conversationId?: string;
}

// ══════════════════════════════════════════════════════════════════════════
// Hook Implementation
// ══════════════════════════════════════════════════════════════════════════

export function useFastAPIChat({
  model = "dynamic_orchestration",
  conversationId: initialConversationId,
}: UseFastAPIChatOptions = {}): UseFastAPIChatReturn {
  // State management
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<Error | null>(null);
  const [conversationId, _setConversationId] = useState<string | undefined>(initialConversationId);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connected");
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [approvalStatuses, setApprovalStatuses] = useState<Record<string, ApprovalActionState>>({});

  // Refs for fetch abort control and streaming
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingMessageRef = useRef<Message | null>(null);
  const isSendingRef = useRef<boolean>(false);
  const messageIdSetRef = useRef<Set<string>>(new Set());

  // WebSocket state
  const [websocketUrl, setWebsocketUrl] = useState<string | null>(null);
  const [_currentExecutionId, _setCurrentExecutionId] = useState<string | null>(null);

  // ══════════════════════════════════════════════════════════════════════════
  // Message Management
  // ══════════════════════════════════════════════════════════════════════════

  const addMessage = useCallback((message: Message) => {
    if (messageIdSetRef.current.has(message.id)) {
      console.warn(`[Dedup] Skipping duplicate message: ${message.id}`);
      return;
    }
    messageIdSetRef.current.add(message.id);
    setMessages((prev) => [...prev, message]);
  }, []);

  const startStreamingMessage = useCallback((id: string, content: string, actor?: string) => {
    if (messageIdSetRef.current.has(id)) {
      console.warn(`[Dedup] Skipping duplicate streaming message: ${id}`);
      return;
    }
    const newMessage: Message = {
      id,
      role: "assistant",
      content,
      actor,
    };
    streamingMessageRef.current = newMessage;
    messageIdSetRef.current.add(id);
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const appendDelta = useCallback((delta: string) => {
    if (streamingMessageRef.current) {
      streamingMessageRef.current.content += delta;
      setMessages((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0) {
          updated[lastIndex] = { ...streamingMessageRef.current! };
        }
        return updated;
      });
    }
  }, []);

  const finishStreaming = useCallback(() => {
    streamingMessageRef.current = null;
    setStatus("ready");
  }, []);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback(
    (message: WebSocketMessage) => {
      try {
        const { type, data } = message;

        switch (type) {
          case "delta":
            // Streaming text delta
            if (data.text && typeof data.text === "string") {
              appendDelta(data.text);
            }
            break;

          case "message":
            // Complete message
            finishStreaming();
            if (data.message && typeof data.message === "object") {
              const msg = data.message as Record<string, unknown>;
              if (msg.content && typeof msg.content === "string") {
                // Message already added via streaming, just finish
              }
            }
            break;

          case "complete":
            // Workflow completed
            finishStreaming();
            setWebsocketUrl(null);
            setCurrentExecutionId(null);
            break;

          case "error":
            // Workflow error
            setStatus("error");
            setError(new Error((data.error as string) || "Workflow execution failed"));
            setWebsocketUrl(null);
            setCurrentExecutionId(null);
            break;

          case "plan.created":
          case "plan.updated":
            if (data.plan) {
              setCurrentPlan(data.plan as Plan);
            }
            break;

          case "queue.status":
            if (data.status) {
              setQueueStatus(data.status as QueueStatus);
            }
            break;

          case "approval.requested": {
            const approval: PendingApproval = {
              id: data.id as string,
              requestId: data.request_id as string,
              operation: data.operation as string,
              description: data.description as string,
              details: data.details as Record<string, unknown>,
              timestamp: Date.now(),
            };
            setPendingApprovals((prev) => [...prev, approval]);
            setApprovalStatuses((prev) => ({ ...prev, [approval.id]: { status: "idle" } }));
            break;
          }

          case "ping":
            // Keepalive ping - ignore
            break;

          default:
            // eslint-disable-next-line no-console
            console.log("Unknown WebSocket message type:", type);
        }
      } catch (err) {
        console.error("Error handling WebSocket message:", err);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [] // Empty deps - appendDelta and finishStreaming are stable useCallbacks, state setters are stable
  );

  // WebSocket connection
  const { isConnected: _isConnected } = useWebSocket({
    url: websocketUrl,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      // eslint-disable-next-line no-console
      console.log("WebSocket connected");
    },
    onClose: () => {
      // eslint-disable-next-line no-console
      console.log("WebSocket disconnected");
      setWebsocketUrl(null);
    },
    onError: (error) => {
      console.error("WebSocket error:", error);
      setStatus("error");
      setError(new Error("WebSocket connection failed"));
    },
    reconnect: false, // Don't auto-reconnect for completed executions
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Message Sending
  // ══════════════════════════════════════════════════════════════════════════

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Prevent duplicate sends
      if (isSendingRef.current) {
        console.warn("Message send already in progress, ignoring duplicate call");
        return;
      }

      isSendingRef.current = true;

      // Add user message with unique ID (timestamp + random component)
      const userMessage: Message = {
        id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        role: "user",
        content: content.trim(),
      };

      console.warn("Adding user message:", userMessage.id);
      addMessage(userMessage);

      setStatus("submitted");
      setError(null);

      try {
        // Create chat execution via POST /v1/chat
        const baseUrl = import.meta.env.VITE_BACKEND_URL || "";
        const url = `${baseUrl}/v1/chat`;

        const payload = {
          message: content.trim(),
          workflow_id: model === "dynamic_orchestration" ? "magentic_fleet" : model,
          ...(conversationId && { conversation_id: conversationId }),
          metadata: {},
        };

        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        const { execution_id, websocket_url } = data;

        if (!websocket_url) {
          throw new Error("No WebSocket URL returned from server");
        }

        // Store execution ID and start streaming
        _setCurrentExecutionId(execution_id);
        setStatus("streaming");

        // Start streaming message with unique ID (timestamp + random component)
        const responseId = `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
        startStreamingMessage(responseId, "", "assistant");

        // Connect to WebSocket (will trigger useWebSocket hook)
        setWebsocketUrl(websocket_url);

        // Reset sending flag after successful connection
        isSendingRef.current = false;
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err : new Error("Failed to send message"));
        // Reset sending flag on error
        isSendingRef.current = false;
      }
    },
    [model, conversationId, addMessage, startStreamingMessage]
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Approval Handling
  // ══════════════════════════════════════════════════════════════════════════

  const respondToApproval = useCallback(
    async (requestId: string, payload: ApprovalResponsePayload) => {
      setApprovalStatuses((prev) => ({
        ...prev,
        [requestId]: { status: "submitting" },
      }));

      try {
        const baseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
        const response = await fetch(`${baseUrl}/v1/approvals/${requestId}/decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision: payload }),
        });

        if (!response.ok) {
          throw new Error(`Failed to submit approval: ${response.status}`);
        }

        setApprovalStatuses((prev) => ({
          ...prev,
          [requestId]: { status: "success" },
        }));

        // Remove from pending
        setPendingApprovals((prev) => prev.filter((a) => a.id !== requestId));
      } catch (err) {
        setApprovalStatuses((prev) => ({
          ...prev,
          [requestId]: {
            status: "error",
            error: err instanceof Error ? err.message : "Unknown error",
          },
        }));
      }
    },
    []
  );

  const refreshApprovals = useCallback(async () => {
    // Placeholder for refreshing approvals from backend
    // This will be implemented when the backend endpoint is available
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // Connection Health
  // ══════════════════════════════════════════════════════════════════════════

  const checkHealth = useCallback(async () => {
    try {
      const baseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/health`);

      if (response.ok) {
        setConnectionStatus("connected");
      } else {
        setConnectionStatus("error");
      }
    } catch {
      setConnectionStatus("disconnected");
    }
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // Effects
  // ══════════════════════════════════════════════════════════════════════════

  // Initial health check
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // Return Hook API
  // ══════════════════════════════════════════════════════════════════════════

  return {
    messages,
    input,
    setInput,
    sendMessage,
    status,
    error,
    currentPlan,
    queueStatus,
    pendingApprovals,
    approvalStatuses,
    respondToApproval,
    refreshApprovals,
    connectionStatus,
    checkHealth,
    conversationId,
  };
}
