import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DashboardPage } from "@/pages/dashboard-page";

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

  it("is a simple wrapper with no additional functionality", () => {
    const { container } = render(<DashboardPage />);

    // Should render exactly what OptimizationDashboard renders
    expect(container.firstChild).toBe(
      screen.getByTestId("optimization-dashboard"),
    );
  });

  it("matches snapshot", () => {
    const { container } = render(<DashboardPage />);
    expect(container).toMatchSnapshot();
  });
});
