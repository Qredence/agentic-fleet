/**
 * Custom React hook for FastAPI HaxUI chat integration with SSE streaming
 * 
 * This hook manages:
 * - SSE connection to FastAPI backend
 * - Message state and history
 * - Pending approval requests (HITL)
 * - Approval response handling
 * - Error handling and status management
 */

import { useCallback, useEffect, useRef, useState } from "react";

// ============================================================================
// Types
// ============================================================================

export type ChatStatus = "ready" | "submitted" | "streaming" | "error";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  actor?: string;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  state: "input-streaming" | "input-available" | "output-available" | "output-error";
  input?: any;
  output?: any;
  errorText?: string;
}

export interface PendingApproval {
  requestId: string;
  functionCall: {
    id: string;
    name: string;
    arguments: Record<string, any>;
  };
}

export type ApprovalActionState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "error"; error: string };

export interface UseFastAPIChatOptions {
  /** Model/entity ID to use (default: 'magentic_fleet') */
  model?: string;
  /** Conversation ID for context */
  conversationId?: string;
  /** Base API URL (default: '/v1') */
  apiUrl?: string;
}

export interface UseFastAPIChatReturn {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  status: ChatStatus;
  error: Error | null;
  sendMessage: (content: string) => Promise<void>;
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  respondToApproval: (requestId: string, approved: boolean) => Promise<void>;
  conversationId?: string;
}

// ============================================================================
// SSE Event Types (from FastAPI backend)
// ============================================================================

interface SSEDeltaEvent {
  type: "response.output_text.delta";
  delta: string;
  item_id: string;
  output_index: number;
  sequence_number: number;
  actor?: string;
  role?: string;
}

interface SSEWorkflowEvent {
  type: "workflow.event";
  actor: string;
  text: string;
  role: string;
  message_id: string;
  sequence_number: number;
}

interface SSECompletedEvent {
  type: "response.completed";
  sequence_number: number;
  response: {
    id: string;
    model: string;
    usage: Record<string, any>;
  };
}

interface SSEApprovalRequestedEvent {
  type: "response.function_approval.requested";
  request_id: string;
  function_call: {
    id: string;
    name: string;
    arguments: Record<string, any>;
  };
  item_id: string;
  output_index: number;
  sequence_number: number;
}

interface SSEApprovalRespondedEvent {
  type: "response.function_approval.responded";
  request_id: string;
  approved: boolean;
  sequence_number: number;
}

interface SSEErrorEvent {
  type: "error";
  error?: {
    type: string;
    message: string;
  };
  message?: string;
  sequence_number: number;
}

type SSEEvent =
  | SSEDeltaEvent
  | SSEWorkflowEvent
  | SSECompletedEvent
  | SSEApprovalRequestedEvent
  | SSEApprovalRespondedEvent
  | SSEErrorEvent;

// ============================================================================
// Hook Implementation
// ============================================================================

export function useFastAPIChat({
  model = "magentic_fleet",
  conversationId: initialConversationId,
  apiUrl = "/v1",
}: UseFastAPIChatOptions = {}): UseFastAPIChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<Error | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(
    initialConversationId
  );
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>(
    []
  );
  const [approvalStatuses, setApprovalStatuses] = useState<
    Record<string, ApprovalActionState>
  >({});

  const abortControllerRef = useRef<AbortController | null>(null);
  const currentAssistantMessageRef = useRef<string>("");
  const currentMessageIdRef = useRef<string>("");

  /**
   * Send a message to the FastAPI backend and handle SSE streaming
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (status === "streaming" || status === "submitted") {
        return; // Prevent duplicate submissions
      }

      setStatus("submitted");
      setError(null);

      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
      };
      setMessages((prev) => [...prev, userMessage]);

      // Reset assistant message accumulation
      currentAssistantMessageRef.current = "";
      currentMessageIdRef.current = "";

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const payload = {
          model,
          conversation: conversationId,
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

        const response = await fetch(`${apiUrl}/responses`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            `Request failed: ${response.status} ${response.statusText}`
          );
        }

        if (!response.body) {
          throw new Error("Response body is null");
        }

        setStatus("streaming");

        // Parse SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

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

              try {
                const event: SSEEvent = JSON.parse(data);
                handleSSEEvent(event);
              } catch (e) {
                console.error("Failed to parse SSE event:", e, data);
              }
            }
          }
        }

        setStatus("ready");
      } catch (err) {
        if (err instanceof Error) {
          if (err.name === "AbortError") {
            console.log("Request aborted");
            setStatus("ready");
          } else {
            console.error("Error sending message:", err);
            setError(err);
            setStatus("error");
          }
        }
      } finally {
        abortControllerRef.current = null;
      }
    },
    [model, conversationId, status, apiUrl]
  );

  /**
   * Handle individual SSE events from the backend
   */
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case "response.output_text.delta": {
        // Accumulate streaming text
        currentAssistantMessageRef.current += event.delta;

        if (!currentMessageIdRef.current) {
          currentMessageIdRef.current = event.item_id;
          // Create assistant message
          setMessages((prev) => [
            ...prev,
            {
              id: event.item_id,
              role: "assistant",
              content: event.delta,
              actor: event.actor,
            },
          ]);
        } else {
          // Update existing message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentMessageIdRef.current
                ? { ...msg, content: currentAssistantMessageRef.current }
                : msg
            )
          );
        }
        break;
      }

      case "workflow.event": {
        // System/workflow messages
        const systemMessage: Message = {
          id: event.message_id,
          role: "system",
          content: event.text,
          actor: event.actor,
        };
        setMessages((prev) => [...prev, systemMessage]);
        break;
      }

      case "response.completed": {
        // Update conversation ID if provided
        const responseConvId = (event.response as any).conversation_id;
        if (responseConvId) {
          setConversationId(responseConvId);
        }
        break;
      }

      case "response.function_approval.requested": {
        // Add pending approval
        const approval: PendingApproval = {
          requestId: event.request_id,
          functionCall: event.function_call,
        };
        setPendingApprovals((prev) => {
          // Avoid duplicates
          if (prev.some((a) => a.requestId === event.request_id)) {
            return prev;
          }
          return [...prev, approval];
        });
        setApprovalStatuses((prev) => ({
          ...prev,
          [event.request_id]: { status: "idle" },
        }));
        break;
      }

      case "response.function_approval.responded": {
        // Remove approval from pending list
        setPendingApprovals((prev) =>
          prev.filter((a) => a.requestId !== event.request_id)
        );
        setApprovalStatuses((prev) => {
          const updated = { ...prev };
          delete updated[event.request_id];
          return updated;
        });
        break;
      }

      case "error": {
        const errorMessage =
          event.error?.message || event.message || "An error occurred";
        setError(new Error(errorMessage));
        setStatus("error");
        break;
      }

      default:
        console.log("Unknown SSE event type:", (event as any).type);
    }
  }, []);

  /**
   * Respond to a pending approval request
   */
  const respondToApproval = useCallback(
    async (requestId: string, approved: boolean) => {
      setApprovalStatuses((prev) => ({
        ...prev,
        [requestId]: { status: "submitting" },
      }));

      try {
        const payload = {
          model,
          conversation: conversationId,
          input: [
            {
              type: "message",
              role: "user",
              content: [
                {
                  type: "function_approval_response",
                  request_id: requestId,
                  approved,
                },
              ],
            },
          ],
        };

        const response = await fetch(`${apiUrl}/responses`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error(
            `Approval response failed: ${response.status} ${response.statusText}`
          );
        }

        // The approval response will be handled via SSE events
        // The backend will send a response.function_approval.responded event
      } catch (err) {
        console.error("Error responding to approval:", err);
        setApprovalStatuses((prev) => ({
          ...prev,
          [requestId]: {
            status: "error",
            error:
              err instanceof Error ? err.message : "Failed to send approval",
          },
        }));
        throw err;
      }
    },
    [model, conversationId, apiUrl]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    input,
    setInput,
    status,
    error,
    sendMessage,
    pendingApprovals,
    approvalStatuses,
    respondToApproval,
    conversationId,
  };
}
