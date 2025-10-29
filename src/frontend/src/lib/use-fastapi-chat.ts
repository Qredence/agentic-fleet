/**
 * useFastAPIChat Hook - Refactored Version
 *
 * Composed from specialized hooks for better maintainability:
 * - useChatSubmission: Message sending logic
 * - useSSEEventProcessor: Event processing and state updates
 * - useConnectionHealth: Health checks and connection monitoring
 * - useChatState: Centralized state management
 * - useConversationManager: Conversation lifecycle
 *
 * This refactored version reduces complexity from 741 lines to ~200 lines
 * while maintaining the same API and functionality.
 */

import { useCallback, useEffect } from "react";
import { useMessageState, type Message } from "./hooks/useMessageState";
import { useApprovalWorkflow, type PendingApproval, type ApprovalResponsePayload } from "./hooks/useApprovalWorkflow";
import { useChatSubmission } from "./hooks/useChatSubmission";
import { useSSEEventProcessor } from "./hooks/useSSEEventProcessor";
import type { Plan } from "./hooks/useSSEEventProcessor";
import { useConnectionHealth } from "./hooks/useConnectionHealth";
import { useChatState } from "./hooks/useChatState";
import { useConversationManager } from "./hooks/useConversationManager";

// Re-export types for consuming components
export type { Message } from "./hooks/useMessageState";
export type {
  ApprovalActionState,
  ApprovalResponsePayload,
  PendingApproval,
} from "./hooks/useApprovalWorkflow";
export type {
  ChatStatus,
  ConnectionStatus,
  QueueStatus,
  Plan,
  WorkflowEventType
} from "./hooks/useChatState";

export interface UseFastAPIChatOptions {
  /** Model/entity ID to use (default: 'dynamic_orchestration') */
  model?: string;
  /** Conversation ID for context */
  conversationId?: string;
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

export function useFastAPIChat({
  model = "dynamic_orchestration",
  conversationId: initialConversationId,
}: UseFastAPIChatOptions = {}): UseFastAPIChatReturn {

  // ══════════════════════════════════════════════════════════════════════════
  // Specialized Hook Composition
  // ══════════════════════════════════════════════════════════════════════════

  const messageState = useMessageState();
  const approvalWorkflow = useApprovalWorkflow();
  const _conversationManager = useConversationManager({
    initialConversationId,
    messageState,
    approvalWorkflow,
  });

  // Centralized state management
  const chatState = useChatState({
    initialConversationId,
  });

  const { setCurrentPlan } = chatState;
  const currentPlan = chatState.state.currentPlan;

  const handlePlanUpdate = useCallback(
    (update: Plan | null | ((prev: Plan | null) => Plan | null)) => {
      const nextPlan = typeof update === "function" ? update(currentPlan) : update;
      setCurrentPlan(nextPlan);
    },
    [currentPlan, setCurrentPlan]
  );

  // Connection health monitoring
  const connectionHealth = useConnectionHealth({
    onStatusChange: chatState.setConnectionStatus,
  });

  const { connectionStatus, resetRetryCount, checkHealth } = connectionHealth;

  // SSE event processing
  const sseProcessor = useSSEEventProcessor({
    onMessageStateAction: (action) => {
      switch (action.type) {
        case "start_streaming":
          if (!messageState.isStreaming()) {
            messageState.startStreamingMessage(
              action.payload.itemId,
              action.payload.delta,
              action.payload.actor
            );
          }
          break;
        case "append_delta":
          messageState.appendDelta(action.payload.delta);
          break;
        case "add_message":
          messageState.addMessage(action.payload);
          break;
        case "finish_streaming":
          messageState.finishStreaming();
          break;
        case "reset_streaming":
          messageState.resetStreaming();
          break;
      }
    },
    onPlanUpdate: handlePlanUpdate,
    onQueueStatusUpdate: chatState.setQueueStatus,
    onApprovalEvent: (event) => {
      if (event.type === "approval_requested") {
        approvalWorkflow.handleApprovalRequested(event.payload);
      } else if (event.type === "approval_responded") {
        approvalWorkflow.handleApprovalResponded(event.payload);
      }
    },
    onError: chatState.setError,
    onStreamingComplete: (conversationId) => {
      chatState.setStatus("ready");
      if (conversationId) {
        chatState.setConversationId(conversationId);
      }
    },
    onStatusChange: chatState.setStatus,
  });

  // Chat submission handling
  const chatSubmission = useChatSubmission({
    model,
    conversationId: chatState.state.conversationId,
    onConversationChange: chatState.setConversationId,
    onStatusChange: chatState.setStatus,
    onError: chatState.setError,
    onAddUserMessage: messageState.addMessage,
    onResetStreaming: messageState.resetStreaming,
    onSSEEvent: sseProcessor.processEvent,
    onStreamingStart: () => chatState.setStatus("streaming"),
    onSubmissionComplete: () => {
      chatState.setStatus("ready");
      approvalWorkflow.fetchApprovals();
    },
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Input Management
  // ══════════════════════════════════════════════════════════════════════════

  const handleInputChange = useCallback((value: string) => {
    chatState.setInput(value);
  }, [chatState]);

  // ══════════════════════════════════════════════════════════════════════════
  // Effects for Cleanup
  // ══════════════════════════════════════════════════════════════════════════

  // Cleanup on unmount - abort any ongoing requests
  useEffect(() => {
    return () => {
      chatSubmission.abortRequest();
    };
  }, [chatSubmission]);

  // Reset connection health retry count when connected
  useEffect(() => {
    if (connectionStatus === "connected") {
      resetRetryCount();
    }
  }, [connectionStatus, resetRetryCount]);

  // ══════════════════════════════════════════════════════════════════════════
  // Return Value - Composed Hook API
  // ══════════════════════════════════════════════════════════════════════════

  return {
    // Message management (from useMessageState)
    messages: messageState.messages,

    // User input
    input: chatState.state.input,
    setInput: handleInputChange,

    // Chat submission and status
    sendMessage: chatSubmission.sendMessage,
    status: chatState.state.status,
    error: chatState.state.error,
    currentPlan: chatState.state.currentPlan,
    queueStatus: chatState.state.queueStatus,

    // Approval workflow (from useApprovalWorkflow)
    pendingApprovals: approvalWorkflow.pendingApprovals,
    approvalStatuses: approvalWorkflow.approvalStatuses,
    respondToApproval: approvalWorkflow.respondToApproval,
    refreshApprovals: approvalWorkflow.fetchApprovals,

    // Connection status
    connectionStatus,
    checkHealth,

    // Conversation context
    conversationId: chatState.state.conversationId,
  };
}
