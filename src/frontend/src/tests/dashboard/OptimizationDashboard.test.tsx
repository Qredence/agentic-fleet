import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OptimizationDashboard } from "@/features/dashboard";

type MockMutation<TData = unknown, TVariables = unknown> = {
  mutate: (variables: TVariables) => void;
  mutateAsync?: (variables: TVariables) => Promise<TData>;
  isPending: boolean;
  isError: boolean;
  data?: TData;
};

type MockQuery<TData = unknown> = {
  data?: TData;
  isLoading: boolean;
  isError: boolean;
  isFetching?: boolean;
  refetch?: () => void;
};

// Mutable state for each hook
let optimizationRun: MockMutation<{ job_id?: string | null }, unknown>;
let optimizationStatus: MockQuery<{ status: string; message: string }>;
let historyQuery: MockQuery<unknown[]>;
let selfImprove: MockMutation<unknown, unknown>;
let dspyConfig: MockQuery<Record<string, unknown>>;
let dspyCacheInfo: MockQuery<{ size?: number; entries?: number }>;
let reasonerSummary: MockQuery<Record<string, unknown>>;
let dspySignatures: MockQuery<Array<{ name: string; description?: string }>>;
let clearCache: MockMutation<unknown, unknown>;
let clearRoutingCache: MockMutation<unknown, unknown>;

vi.mock("@/api/hooks", () => ({
  useOptimizationRun: () => optimizationRun,
  useOptimizationStatus: () => optimizationStatus,
  useEvaluationHistory: () => historyQuery,
  useTriggerSelfImprove: () => selfImprove,
  useDSPyConfig: () => dspyConfig,
  useDSPyCacheInfo: () => dspyCacheInfo,
  useReasonerSummary: () => reasonerSummary,
  useDSPySignatures: () => dspySignatures,
  useClearDSPyCache: () => clearCache,
  useClearRoutingCache: () => clearRoutingCache,
}));

beforeEach(() => {
  optimizationRun = {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    data: undefined,
  };
  optimizationStatus = {
    isLoading: false,
    isError: false,
    data: { status: "completed", message: "ok" },
  };
  historyQuery = {
    isLoading: false,
    isError: false,
    data: [],
    isFetching: false,
  };
  selfImprove = {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    data: undefined,
  };
  dspyConfig = {
    isLoading: false,
    isError: false,
    data: {},
  };
  dspyCacheInfo = {
    isLoading: false,
    isError: false,
    data: { size: 0, entries: 0 },
  };
  reasonerSummary = {
    isLoading: false,
    isError: false,
    data: {},
  };
  dspySignatures = {
    isLoading: false,
    isError: false,
    data: [],
  };
  clearCache = {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  };
  clearRoutingCache = {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  };
});

describe("OptimizationDashboard", () => {
  it("renders and starts optimization when clicking Start Optimization", async () => {
    const user = userEvent.setup();
    render(<OptimizationDashboard />);

    // Button text is "Start Optimization" in the current UI
    await user.click(
      screen.getByRole("button", { name: /start optimization/i }),
    );

    expect(optimizationRun.mutate).toHaveBeenCalledTimes(1);
  });

  it("renders history loading state", async () => {
    historyQuery = { isLoading: true, isError: false, data: undefined };
    const user = userEvent.setup();
    render(<OptimizationDashboard />);

    // Click the History tab to see the loading state
    await user.click(screen.getByRole("tab", { name: /history/i }));

    // The component shows "Loading history..." when history is loading
    expect(screen.getByText(/loading history/i)).toBeInTheDocument();
  });

  it("renders self-improvement error state", async () => {
    selfImprove = { mutate: vi.fn(), isPending: false, isError: true };
    const user = userEvent.setup();
    render(<OptimizationDashboard />);

    // Click the Self-Improve tab to see the error state
    await user.click(screen.getByRole("tab", { name: /self-improve/i }));

    // Error message shown in the Self-Improve tab
    expect(screen.getByText(/self-improvement failed/i)).toBeInTheDocument();
  });
});
