import { create } from "zustand";

interface AgentMetrics {
  messages: number;
  lastMessageAt: number | null;
}

interface Totals {
  messages: number;
  agents: number;
  errors: number;
}

interface PerformanceMetrics {
  lastResponseMs: number | null;
  avgResponseMs: number | null;
}

interface MetricsState {
  startedAt: number;
  totals: Totals;
  perAgent: Record<string, AgentMetrics>;
  performance: PerformanceMetrics;
}

interface MetricsActions {
  incrementMessage: (agentId: string | undefined) => void;
  recordError: () => void;
  resetMetrics: () => void;
}

export type MetricsStore = MetricsState & MetricsActions;

const initialState = (): MetricsState => ({
  startedAt: Date.now(),
  totals: {
    messages: 0,
    agents: 0,
    errors: 0,
  },
  perAgent: {},
  performance: {
    lastResponseMs: null,
    avgResponseMs: null,
  },
});

export const useMetricsStore = create<MetricsStore>((set) => ({
  ...initialState(),

  incrementMessage: (agentId) => {
    set((state) => {
      const now = Date.now();
      if (!agentId) {
        return {
          totals: {
            ...state.totals,
            messages: state.totals.messages + 1,
          },
          performance: state.performance,
          perAgent: state.perAgent,
        };
      }

      const existing = state.perAgent[agentId];
      const nextAgent: AgentMetrics = existing
        ? {
            messages: existing.messages + 1,
            lastMessageAt: now,
          }
        : {
            messages: 1,
            lastMessageAt: now,
          };

      const nextAgents = {
        ...state.perAgent,
        [agentId]: nextAgent,
      };

      const nextTotals: Totals = {
        messages: state.totals.messages + 1,
        agents: existing ? state.totals.agents : state.totals.agents + 1,
        errors: state.totals.errors,
      };

      return {
        totals: nextTotals,
        perAgent: nextAgents,
        performance: state.performance,
      };
    });
  },

  recordError: () => {
    set((state) => ({
      totals: {
        ...state.totals,
        errors: state.totals.errors + 1,
      },
    }));
  },

  resetMetrics: () => {
    set(() => initialState());
  },
}));
