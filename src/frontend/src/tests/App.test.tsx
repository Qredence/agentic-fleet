import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import App from "@/App";

// Mock child components to isolate App testing
vi.mock("@/components/chat/ConversationSidebar", () => ({
  ConversationSidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock("@/components/chat/ChatContainer", () => ({
  ChatContainer: () => <div data-testid="chat-container">ChatContainer</div>,
}));

describe("App", () => {
  it("renders sidebar and chat container", () => {
    render(<App />);

    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("chat-container")).toBeInTheDocument();
  });

  it("has correct layout classes", () => {
    const { container } = render(<App />);
    // Check for flex layout classes
    expect(container.firstChild).toHaveClass(
      "flex",
      "h-screen",
      "w-screen",
      "overflow-hidden",
    );
  });
});
