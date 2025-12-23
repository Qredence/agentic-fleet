/**
 * Mock data factories for testing
 *
 * Generates consistent mock data for tests using faker.js patterns
 */

import type {
  Conversation,
  Message,
  WorkflowSession,
  AgentInfo,
  OptimizationResult,
  HistoryExecutionEntry,
} from "@/api/types";
import { vi } from "vitest";

/**
 * Creates a mock conversation with realistic data
 */
export function createMockConversation(
  overrides?: Partial<Conversation>,
): Conversation {
  const id = `conv-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  const timestamp = new Date().toISOString();

  return {
    conversation_id: id,
    title: `Test Conversation ${Math.floor(Math.random() * 1000)}`,
    created_at: timestamp,
    updated_at: timestamp,
    messages: [],
    ...overrides,
  };
}

/**
 * Creates a mock message with realistic data
 */
export function createMockMessage(overrides?: Partial<Message>): Message {
  const id = `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  const timestamp = new Date().toISOString();

  return {
    id,
    role: "user",
    content: "Hello, this is a test message.",
    created_at: timestamp,
    ...overrides,
  };
}

/**
 * Creates a mock user message
 */
export function createMockUserMessage(
  content: string,
  overrides?: Partial<Message>,
): Message {
  return createMockMessage({
    role: "user",
    content,
    ...overrides,
  });
}

/**
 * Creates a mock assistant message
 */
export function createMockAssistantMessage(
  content: string,
  overrides?: Partial<Message>,
): Message {
  return createMockMessage({
    role: "assistant",
    content,
    ...overrides,
  });
}

/**
 * Creates a mock workflow session
 */
export function createMockWorkflowSession(
  overrides?: Partial<WorkflowSession>,
): WorkflowSession {
  const timestamp = new Date().toISOString();
  return {
    workflow_id: `session-${Date.now()}`,
    task: "Test task",
    status: "running",
    created_at: timestamp,
    ...overrides,
  };
}

/**
 * Creates a mock agent info
 */
export function createMockAgentInfo(overrides?: Partial<AgentInfo>): AgentInfo {
  return {
    name: `Test Agent ${Math.floor(Math.random() * 100)}`,
    description: "A test agent for testing purposes",
    type: "test",
    ...overrides,
  };
}

/**
 * Creates a mock optimization result
 */
export function createMockOptimizationResult(
  overrides?: Partial<OptimizationResult>,
): OptimizationResult {
  return {
    job_id: `opt-${Date.now()}`,
    status: "completed",
    created_at: new Date().toISOString(),
    message: "Optimization completed successfully",
    ...overrides,
  };
}

/**
 * Creates a mock history execution entry
 */
export function createMockHistoryExecutionEntry(
  overrides?: Partial<HistoryExecutionEntry>,
): HistoryExecutionEntry {
  return {
    workflow_id: `hist-${Date.now()}`,
    created_at: new Date().toISOString(),
    status: "completed",
    ...overrides,
  };
}

/**
 * Creates a mock store state for chat store tests
 */
export function createMockChatStoreState(
  overrides?: Partial<ReturnType<typeof import("@/stores").useChatStore>>,
): ReturnType<typeof import("@/stores").useChatStore> {
  return {
    messages: [],
    conversations: [],
    conversationId: null,
    activeView: "chat",
    showTrace: true,
    showRawReasoning: false,
    isLoading: false,
    isInitializing: false,
    isConversationsLoading: false,
    currentReasoning: "",
    isReasoningStreaming: false,
    currentWorkflowPhase: "",
    currentAgent: null,
    completedPhases: [],
    sendMessage: vi.fn(),
    createConversation: vi.fn(),
    cancelStreaming: vi.fn(),
    selectConversation: vi.fn(),
    loadConversations: vi.fn(),
    setActiveView: vi.fn(),
    setShowTrace: vi.fn(),
    setShowRawReasoning: vi.fn(),
    ...overrides,
  } as ReturnType<typeof import("@/stores").useChatStore>;
}

/**
 * Creates a mock React Query hook result
 */
export function createMockQueryResult<T = unknown>(
  data?: T,
  overrides?: Partial<{
    data: T | undefined;
    isLoading: boolean;
    isError: boolean;
    isFetching: boolean;
    error: Error | null;
    refetch: () => void;
  }>,
) {
  return {
    data,
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  };
}

/**
 * Creates a mock React Query mutation result
 */
export function createMockMutationResult<TData = unknown, TVariables = unknown>(
  overrides?: Partial<{
    mutate: (variables: TVariables) => void;
    mutateAsync: (variables: TVariables) => Promise<TData>;
    isPending: boolean;
    isError: boolean;
    isSuccess: boolean;
    error: Error | null;
    data: TData | undefined;
  }>,
) {
  return {
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({} as TData),
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    data: undefined,
    ...overrides,
  };
}
