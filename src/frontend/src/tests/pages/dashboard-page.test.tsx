import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders as render } from "@/tests/utils/render";

import { DashboardPage } from "../../pages";

// Mock the OptimizationDashboard component
vi.mock("@/components/dashboard", () => ({
  OptimizationDashboard: vi.fn(() => (
    <div data-testid="optimization-dashboard">
      <h1>Optimization Dashboard</h1>
      <button data-testid="start-optimization">Start Optimization</button>
      <div data-testid="status">Status: Completed</div>
    </div>
  )),
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the OptimizationDashboard component", () => {
    render(<DashboardPage />);

    expect(screen.getByTestId("optimization-dashboard")).toBeInTheDocument();
    expect(screen.getByText("Optimization Dashboard")).toBeInTheDocument();
  });

  it("renders dashboard with sidebar", () => {
    const { container } = render(<DashboardPage />);

    // Should render dashboard component
    expect(screen.getByTestId("optimization-dashboard")).toBeInTheDocument();
    // Container should have the dashboard content
    expect(container.querySelector("main")).toBeInTheDocument();
  });

  it("matches snapshot", () => {
    const { container } = render(<DashboardPage />);
    expect(container).toMatchSnapshot();
  });
});
