import type { Message, ReasoningEffort } from "@/api/types";

export interface SendMessageOptions {
  reasoning_effort?: ReasoningEffort;
  enable_checkpointing?: boolean;
}

export interface ChatState {
  // Data
  messages: Message[];
  conversationId: string | null;

  // UI preferences
  showTrace: boolean;
  showRawReasoning: boolean;
  executionMode: "auto" | "fast" | "standard";
  enableGepa: boolean;

  // Loading states
  isLoading: boolean;
  isInitializing: boolean;

  // Streaming state
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  currentAgent: string | null;
  completedPhases: string[];
  isConcurrentError: boolean;

  // Actions
  selectConversation: (id: string) => Promise<void>;
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  sendWorkflowResponse: (requestId: string, response: unknown) => void;
  cancelStreaming: () => void;
  setMessages: (messages: Message[]) => void;
  setShowTrace: (show: boolean) => void;
  setShowRawReasoning: (show: boolean) => void;
  setExecutionMode: (mode: "auto" | "fast" | "standard") => void;
  setEnableGepa: (enable: boolean) => void;
  reset: () => void;
}
