import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OptimizationDashboard } from "@/components/blocks/optimization-dashboard";

type MockMutation<TData = unknown, TVariables = unknown> = {
  mutate: (variables: TVariables) => void;
  isPending: boolean;
  isError: boolean;
  data?: TData;
};

type MockQuery<TData = unknown> = {
  data?: TData;
  isLoading: boolean;
  isError: boolean;
  isFetching?: boolean;
};

let optimizationRun: MockMutation<{ job_id?: string | null }, unknown>;
let optimizationStatus: MockQuery<{ status: string; message: string }>;
let historyQuery: MockQuery<unknown[]>;
let selfImprove: MockMutation<unknown, unknown>;

vi.mock("@/api/hooks", () => ({
  useOptimizationRun: () => optimizationRun,
  useOptimizationStatus: () => optimizationStatus,
  useEvaluationHistory: () => historyQuery,
  useTriggerSelfImprove: () => selfImprove,
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
});

describe("OptimizationDashboard", () => {
  it("renders and starts optimization when clicking Start run", async () => {
    const user = userEvent.setup();
    render(<OptimizationDashboard />);

    await user.click(
      screen.getByRole("button", { name: /start optimization run/i }),
    );

    expect(optimizationRun.mutate).toHaveBeenCalledTimes(1);
  });

  it("renders history loading state", () => {
    historyQuery = { isLoading: true, isError: false, data: undefined };
    render(<OptimizationDashboard />);

    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });

  it("renders self-improvement error state", () => {
    selfImprove = { mutate: vi.fn(), isPending: false, isError: true };
    render(<OptimizationDashboard />);

    expect(screen.getByText(/self-improvement failed/i)).toBeInTheDocument();
  });
});
