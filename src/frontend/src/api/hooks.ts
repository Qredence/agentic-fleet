/**
 * React Query Hooks
 *
 * TanStack Query hooks for server state management.
 * Handles caching, refetching, and optimistic updates.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import {
  conversationsApi,
  sessionsApi,
  agentsApi,
  healthApi,
  optimizationApi,
  evaluationApi,
  improvementApi,
  dspyApi,
} from "./client";
import type {
  Conversation,
  Message,
  WorkflowSession,
  AgentInfo,
  OptimizationResult,
  OptimizationRequest,
  HistoryExecutionEntry,
  SelfImproveRequest,
  SelfImproveResponse,
  DSPyConfig,
  DSPyStats,
  CacheInfo,
  ReasonerSummary,
  DSPySignatures,
  DSPyPrompts,
} from "./types";
import type { HealthResponse, ReadinessResponse } from "./client";

// =============================================================================
// Query Keys
// =============================================================================

export const queryKeys = {
  conversations: {
    all: ["conversations"] as const,
    list: () => [...queryKeys.conversations.all, "list"] as const,
    detail: (id: string) =>
      [...queryKeys.conversations.all, "detail", id] as const,
    messages: (id: string) =>
      [...queryKeys.conversations.all, "messages", id] as const,
  },
  sessions: {
    all: ["sessions"] as const,
    list: () => [...queryKeys.sessions.all, "list"] as const,
    detail: (id: string) => [...queryKeys.sessions.all, "detail", id] as const,
  },
  agents: {
    all: ["agents"] as const,
    list: () => [...queryKeys.agents.all, "list"] as const,
  },
  optimization: {
    all: ["optimization"] as const,
    status: (jobId: string) =>
      [...queryKeys.optimization.all, "status", jobId] as const,
  },
  history: {
    all: ["history"] as const,
    page: (limit: number, offset: number) =>
      [...queryKeys.history.all, "page", limit, offset] as const,
  },
  health: {
    check: ["health", "check"] as const,
    ready: ["health", "ready"] as const,
  },
  dspy: {
    all: ["dspy"] as const,
    config: () => [...queryKeys.dspy.all, "config"] as const,
    stats: () => [...queryKeys.dspy.all, "stats"] as const,
    cache: () => [...queryKeys.dspy.all, "cache"] as const,
    reasonerSummary: () => [...queryKeys.dspy.all, "reasoner-summary"] as const,
    signatures: () => [...queryKeys.dspy.all, "signatures"] as const,
    prompts: () => [...queryKeys.dspy.all, "prompts"] as const,
  },
} as const;

// =============================================================================
// Conversations Hooks
// =============================================================================

export function useConversations(
  options?: Omit<UseQueryOptions<Conversation[]>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.conversations.list(),
    queryFn: conversationsApi.list,
    staleTime: 30_000, // 30 seconds
    ...options,
  });
}

export function useConversation(
  id: string | null,
  options?: Omit<
    UseQueryOptions<Conversation>,
    "queryKey" | "queryFn" | "enabled"
  >,
) {
  return useQuery({
    queryKey: queryKeys.conversations.detail(id ?? ""),
    queryFn: () => conversationsApi.get(id!),
    enabled: !!id,
    staleTime: 60_000, // 1 minute
    ...options,
  });
}

export function useConversationMessages(
  id: string | null,
  options?: Omit<
    UseQueryOptions<Message[]>,
    "queryKey" | "queryFn" | "enabled"
  >,
) {
  return useQuery({
    queryKey: queryKeys.conversations.messages(id ?? ""),
    queryFn: () => conversationsApi.getMessages(id!),
    enabled: !!id,
    staleTime: 0, // Always refetch messages
    ...options,
  });
}

export function useCreateConversation(
  options?: UseMutationOptions<Conversation, Error, string>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (title: string) => conversationsApi.create(title),
    onSuccess: (newConversation) => {
      // Add to list cache
      queryClient.setQueryData<Conversation[]>(
        queryKeys.conversations.list(),
        (old) => (old ? [newConversation, ...old] : [newConversation]),
      );
      // Set detail cache
      queryClient.setQueryData(
        queryKeys.conversations.detail(newConversation.id),
        newConversation,
      );
    },
    ...options,
  });
}

// =============================================================================
// Sessions Hooks
// =============================================================================

export function useSessions(
  options?: Omit<UseQueryOptions<WorkflowSession[]>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.sessions.list(),
    queryFn: sessionsApi.list,
    staleTime: 10_000, // 10 seconds
    ...options,
  });
}

export function useSession(
  id: string | null,
  options?: Omit<
    UseQueryOptions<WorkflowSession>,
    "queryKey" | "queryFn" | "enabled"
  >,
) {
  return useQuery({
    queryKey: queryKeys.sessions.detail(id ?? ""),
    queryFn: () => sessionsApi.get(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      // Refetch every 2 seconds while running
      const data = query.state.data;
      return data?.status === "running" ? 2000 : false;
    },
    ...options,
  });
}

export function useCancelSession(
  options?: UseMutationOptions<void, Error, string>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: sessionsApi.cancel,
    onSuccess: (_, sessionId) => {
      // Update session status in cache
      queryClient.setQueryData<WorkflowSession>(
        queryKeys.sessions.detail(sessionId),
        (old) => (old ? { ...old, status: "cancelled" } : old),
      );
      // Invalidate list
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions.list() });
    },
    ...options,
  });
}

// =============================================================================
// Agents Hooks
// =============================================================================

export function useAgents(
  options?: Omit<UseQueryOptions<AgentInfo[]>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.agents.list(),
    queryFn: agentsApi.list,
    staleTime: 5 * 60_000, // 5 minutes - agents don't change often
    ...options,
  });
}

// =============================================================================
// Health Hooks
// =============================================================================

export function useHealthCheck(
  options?: Omit<UseQueryOptions<HealthResponse>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.health.check,
    queryFn: healthApi.check,
    staleTime: 30_000,
    retry: false,
    ...options,
  });
}

export function useReadinessCheck(
  options?: Omit<UseQueryOptions<ReadinessResponse>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.health.ready,
    queryFn: healthApi.ready,
    staleTime: 10_000,
    retry: false,
    ...options,
  });
}

// =============================================================================
// Optimization / Evaluation / Self-Improvement Hooks
// =============================================================================

export function useOptimizationRun(
  options?: UseMutationOptions<OptimizationResult, Error, OptimizationRequest>,
) {
  return useMutation({
    mutationFn: optimizationApi.run,
    ...options,
  });
}

export function useOptimizationStatus(
  jobId: string | null,
  options?: Omit<
    UseQueryOptions<OptimizationResult>,
    "queryKey" | "queryFn" | "enabled" | "refetchInterval"
  >,
) {
  return useQuery({
    queryKey: queryKeys.optimization.status(jobId ?? ""),
    queryFn: () => optimizationApi.status(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return 2000;
      return status === "started" || status === "running" ? 2000 : false;
    },
    ...options,
  });
}

export function useEvaluationHistory(
  params: { limit: number; offset: number },
  options?: Omit<
    UseQueryOptions<HistoryExecutionEntry[]>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: queryKeys.history.page(params.limit, params.offset),
    queryFn: () => evaluationApi.history(params),
    staleTime: 5_000,
    ...options,
  });
}

export function useTriggerSelfImprove(
  options?: UseMutationOptions<SelfImproveResponse, Error, SelfImproveRequest>,
) {
  return useMutation({
    mutationFn: improvementApi.trigger,
    ...options,
  });
}

// =============================================================================
// DSPy Management Hooks
// =============================================================================

export function useDSPyConfig(
  options?: Omit<UseQueryOptions<DSPyConfig>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.config(),
    queryFn: dspyApi.getConfig,
    staleTime: 60_000, // 1 minute
    ...options,
  });
}

export function useDSPyStats(
  options?: Omit<UseQueryOptions<DSPyStats>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.stats(),
    queryFn: dspyApi.getStats,
    staleTime: 10_000, // 10 seconds
    ...options,
  });
}

export function useDSPyCacheInfo(
  options?: Omit<UseQueryOptions<CacheInfo>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.cache(),
    queryFn: dspyApi.getCacheInfo,
    staleTime: 30_000, // 30 seconds
    ...options,
  });
}

export function useReasonerSummary(
  options?: Omit<UseQueryOptions<ReasonerSummary>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.reasonerSummary(),
    queryFn: dspyApi.getReasonerSummary,
    staleTime: 10_000, // 10 seconds
    ...options,
  });
}

export function useDSPySignatures(
  options?: Omit<UseQueryOptions<DSPySignatures>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.signatures(),
    queryFn: dspyApi.getSignatures,
    staleTime: 5 * 60_000, // 5 minutes - signatures rarely change
    ...options,
  });
}

export function useDSPyPrompts(
  options?: Omit<UseQueryOptions<DSPyPrompts>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: queryKeys.dspy.prompts(),
    queryFn: dspyApi.getPrompts,
    staleTime: 60_000, // 1 minute
    ...options,
  });
}

export function useClearDSPyCache(options?: UseMutationOptions<void, Error>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dspyApi.clearCache,
    onSuccess: () => {
      // Invalidate cache-related queries
      queryClient.invalidateQueries({ queryKey: queryKeys.dspy.cache() });
      queryClient.invalidateQueries({ queryKey: queryKeys.dspy.stats() });
    },
    ...options,
  });
}

export function useClearRoutingCache(
  options?: UseMutationOptions<void, Error>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dspyApi.clearRoutingCache,
    onSuccess: () => {
      // Invalidate reasoner summary since routing cache size changed
      queryClient.invalidateQueries({
        queryKey: queryKeys.dspy.reasonerSummary(),
      });
    },
    ...options,
  });
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Hook to invalidate all conversation-related queries.
 * Useful after sending a message.
 */
export function useInvalidateConversations() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all }),
    invalidateList: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversations.list(),
      }),
    invalidateDetail: (id: string) =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversations.detail(id),
      }),
    invalidateMessages: (id: string) =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversations.messages(id),
      }),
  };
}
