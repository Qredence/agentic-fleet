/**
 * useFastAPIChat Hook - Consolidated Implementation
 *
 * A simplified, working implementation that provides all the functionality
 * needed for the chat interface. This consolidates message management,
 * SSE streaming, approvals, and connection health in a single hook.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket, type WebSocketMessage } from "./hooks/useWebSocket";
import { createChatExecution } from "./api/chat";
import { listApprovals, submitApprovalDecision } from "./api/approvals";
import { checkHealth as requestHealth } from "./api/health";
import { ApiError } from "./api/client";
import type {
  ApprovalActionState,
  ApprovalResponsePayload,
  ChatStatus,
  ConnectionStatus,
  Message,
  PendingApproval,
  Plan,
  QueueStatus,
  ChatExecutionRequest,
  ApprovalDecisionPayload,
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
              const messageId =
                (typeof msg.id === "string" && msg.id) ||
                streamingMessageRef.current?.id ||
                `assistant-${Date.now()}`;
              const content =
                typeof msg.content === "string"
                  ? msg.content
                  : streamingMessageRef.current?.content ?? "";
              const agentRole =
                typeof msg.agent_type === "string" ? msg.agent_type : undefined;

              setMessages((prev) => {
                const index = prev.findIndex((item) => item.id === messageId);
                if (index === -1) {
                  return [
                    ...prev,
                    {
                      id: messageId,
                      role: "assistant",
                      content,
                      agentRole: agentRole as Message["agentRole"],
                    },
                  ];
                }

                const updated = [...prev];
                updated[index] = {
                  ...updated[index],
                  content,
                  agentRole: agentRole as Message["agentRole"],
                };
                return updated;
              });
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
            const requestId =
              (typeof data.request_id === "string" && data.request_id) ||
              (typeof data.id === "string" && data.id) ||
              `approval-${Date.now()}`;
            const approval: PendingApproval = {
              id: requestId,
              requestId,
              operation:
                typeof data.operation === "string" ? data.operation : undefined,
              description:
                typeof data.description === "string" ? data.description : undefined,
              details: (data.details ?? {}) as Record<string, unknown>,
              timestamp: Date.now(),
              riskLevel:
                typeof data.risk_level === "string"
                  ? (data.risk_level.toLowerCase() as PendingApproval["riskLevel"])
                  : undefined,
            };
            setPendingApprovals((prev) => {
              if (prev.some((item) => item.requestId === requestId)) {
                return prev;
              }
              return [...prev, approval];
            });
            setApprovalStatuses((prev) => ({
              ...prev,
              [requestId]: prev[requestId] ?? { status: "idle" },
            }));
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
  useWebSocket({
    url: websocketUrl,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      setConnectionStatus("connected");
    },
    onClose: () => {
      setConnectionStatus("disconnected");
      setWebsocketUrl(null);
    },
    onError: (error) => {
      console.error("WebSocket error:", error);
      setConnectionStatus("error");
      setStatus("error");
      setError(new Error("WebSocket connection failed"));
    },
    reconnect: false,
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
        const payload: ChatExecutionRequest = {
          message: content.trim(),
          workflow_id: model === "dynamic_orchestration" ? "magentic_fleet" : model,
          metadata: {},
        };

        if (conversationId) {
          payload.conversation_id = conversationId;
        }

        const data = await createChatExecution(payload);
        if (!data.websocket_url) {
          throw new Error("No WebSocket URL returned from server");
        }

        _setCurrentExecutionId(data.execution_id);
        setStatus("streaming");

        const responseId = `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
        startStreamingMessage(responseId, "", "assistant");

        setWebsocketUrl(data.websocket_url);
      } catch (err) {
        const error = (() => {
          if (err instanceof ApiError) {
            const detail =
              typeof err.body === "object" && err.body !== null && "detail" in err.body
                ? String((err.body as Record<string, unknown>).detail)
                : undefined;
            return new Error(detail ?? `API request failed (${err.status})`);
          }
          if (err instanceof Error) {
            return err;
          }
          return new Error("Failed to send message");
        })();
        setStatus("error");
        setError(error);
      } finally {
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
        const decisionPayload: ApprovalDecisionPayload = (() => {
          switch (payload.type) {
            case "approve":
              return {
                decision: "approved",
                reason: payload.reason ?? null,
              };
            case "reject":
              return {
                decision: "rejected",
                reason: payload.reason,
              };
            case "modify":
              return {
                decision: "modified",
                reason: payload.reason ?? null,
                modified_code: payload.modifiedCode ?? null,
                modified_params: payload.modifiedParams ?? null,
              };
            default: {
              const exhaustiveCheck: never = payload;
              return exhaustiveCheck;
            }
          }
        })();

        await submitApprovalDecision(requestId, decisionPayload);

        setApprovalStatuses((prev) => ({
          ...prev,
          [requestId]: { status: "success" },
        }));
        setPendingApprovals((prev) =>
          prev.filter((approval) => approval.requestId !== requestId)
        );
      } catch (err) {
        setApprovalStatuses((prev) => ({
          ...prev,
          [requestId]: {
            status: "error",
            error: err instanceof Error ? err.message : "Unknown error",
          },
        }));
        throw err;
      }
    },
    []
  );

  const refreshApprovals = useCallback(async () => {
    const payload = await listApprovals();

    const nextApprovals = payload.map<PendingApproval>((entry) => {
      const details = (entry.details ?? {}) as Record<string, unknown>;
      return {
        id: entry.request_id,
        requestId: entry.request_id,
        details,
        operation: typeof details?.operation === "string" ? (details.operation as string) : undefined,
        description:
          typeof details?.description === "string"
            ? (details.description as string)
            : undefined,
        timestamp: Date.now(),
        riskLevel:
          typeof details?.risk_level === "string"
            ? (details.risk_level as PendingApproval["riskLevel"])
            : undefined,
      };
    });

    setPendingApprovals(nextApprovals);
    setApprovalStatuses((prev) => {
      const next: Record<string, ApprovalActionState> = {};
      for (const approval of nextApprovals) {
        next[approval.requestId] = prev[approval.requestId] ?? { status: "idle" };
      }
      return next;
    });
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // Connection Health
  // ══════════════════════════════════════════════════════════════════════════

  const checkHealth = useCallback(async () => {
    try {
      const response = await requestHealth();

      if (response.status === "ok") {
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
