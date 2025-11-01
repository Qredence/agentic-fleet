/**
 * Hooks Index
 *
 * Central export point for all custom hooks
 */

export { useMessageState } from "./useMessageState";
export type {
  Message,
  ToolCall,
  UseMessageStateReturn,
} from "./useMessageState";

export { useApprovalWorkflow } from "./useApprovalWorkflow";
export type {
  PendingApproval,
  ApprovalActionState,
  ApprovalResponsePayload,
  UseApprovalWorkflowReturn,
} from "./useApprovalWorkflow";

export { useConversationHistory } from "./useConversationHistory";
export type { UseConversationHistoryReturn } from "./useConversationHistory";
