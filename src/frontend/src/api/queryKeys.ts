// =============================================================================
// Query Keys
// =============================================================================

export const queryKeys = {
  conversations: {
    all: ["conversations"] as const,
    list: () => [...queryKeys.conversations.all, "list"] as const,
    listInfinite: () =>
      [...queryKeys.conversations.all, "listInfinite"] as const,
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
