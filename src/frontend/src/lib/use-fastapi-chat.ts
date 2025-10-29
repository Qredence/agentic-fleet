/**
 * useFastAPIChat Hook - Consolidated Implementation
 *
 * A simplified, working implementation that provides all the functionality
 * needed for the chat interface. This consolidates message management,
 * SSE streaming, approvals, and connection health in a single hook.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Message,
  ChatStatus,
  ConnectionStatus,
  Plan,
  QueueStatus,
  PendingApproval,
  ApprovalActionState,
  ApprovalResponsePayload,
} from "./types";

// Re-export types for consuming components
export type {
  Message,
  ChatStatus,
  ConnectionStatus,
  Plan,
  QueueStatus,
  PendingApproval,
  ApprovalActionState,
  ApprovalResponsePayload,
  WorkflowEventType,
  ToolCall,
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
  const [conversationId, setConversationId] = useState<string | undefined>(initialConversationId);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connected");
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [approvalStatuses, setApprovalStatuses] = useState<Record<string, ApprovalActionState>>({});

  // Refs for SSE and streaming
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingMessageRef = useRef<Message | null>(null);

  // ══════════════════════════════════════════════════════════════════════════
  // Message Management
  // ══════════════════════════════════════════════════════════════════════════

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const startStreamingMessage = useCallback((id: string, content: string, actor?: string) => {
    const newMessage: Message = {
      id,
      role: "assistant",
      content,
      timestamp: Date.now(),
      actor,
    };
    streamingMessageRef.current = newMessage;
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

  // ══════════════════════════════════════════════════════════════════════════
  // SSE Event Processing
  // ══════════════════════════════════════════════════════════════════════════

  const processSSEEvent = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      // Handle different event types
      if (data.type === "response.delta") {
        if (data.delta?.content) {
          appendDelta(data.delta.content);
        }
      } else if (data.type === "response.done") {
        finishStreaming();
        if (data.conversation_id) {
          setConversationId(data.conversation_id);
        }
      } else if (data.type === "plan.created" || data.type === "plan.updated") {
        setCurrentPlan(data.plan);
      } else if (data.type === "queue.status") {
        setQueueStatus(data.status);
      } else if (data.type === "approval.requested") {
        const approval: PendingApproval = {
          id: data.id,
          requestId: data.request_id,
          operation: data.operation,
          description: data.description,
          details: data.details,
          timestamp: Date.now(),
        };
        setPendingApprovals((prev) => [...prev, approval]);
        setApprovalStatuses((prev) => ({ ...prev, [data.id]: { status: "idle" } }));
      }
    } catch (err) {
      console.error("Error processing SSE event:", err);
    }
  }, [appendDelta, finishStreaming]);

  // ══════════════════════════════════════════════════════════════════════════
  // Message Sending
  // ══════════════════════════════════════════════════════════════════════════

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content.trim(),
      timestamp: Date.now(),
    };
    addMessage(userMessage);

    setStatus("submitted");
    setError(null);

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      // Start SSE connection
      const baseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
      const params = new URLSearchParams({
        model,
        prompt: content.trim(),
      });
      
      if (conversationId) {
        params.append("conversation_id", conversationId);
      }

      const url = `${baseUrl}/v1/responses?${params.toString()}`;
      
      eventSourceRef.current = new EventSource(url);
      
      eventSourceRef.current.onmessage = processSSEEvent;
      
      eventSourceRef.current.onerror = () => {
        eventSourceRef.current?.close();
        eventSourceRef.current = null;
        setStatus("error");
        setError(new Error("SSE connection error"));
      };

      // Start streaming state
      setStatus("streaming");
      const responseId = `assistant-${Date.now()}`;
      startStreamingMessage(responseId, "", "assistant");

    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err : new Error("Failed to send message"));
    }
  }, [model, conversationId, addMessage, processSSEEvent, startStreamingMessage]);

  // ══════════════════════════════════════════════════════════════════════════
  // Approval Handling
  // ══════════════════════════════════════════════════════════════════════════

  const respondToApproval = useCallback(async (requestId: string, payload: ApprovalResponsePayload) => {
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
  }, []);

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
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
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
