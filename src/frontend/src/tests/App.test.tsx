import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import App from "@/App";

// Mock child components to isolate App testing
// Actual paths based on file list: components/Sidebar.tsx, components/InputBar.tsx
// It seems ChatContainer and ConversationsSidebar might have been placeholders or from a previous structure.
// In App.tsx:
// import { Sidebar } from './components/Sidebar';
// import { MessageBubble } from './components/MessageBubble';
// import { InputBar } from './components/InputBar';

vi.mock("@/components/Sidebar", () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock("@/components/InputBar", () => ({
  InputBar: () => <div data-testid="input-bar">InputBar</div>,
}));

vi.mock("@/components/MessageBubble", () => ({
  MessageBubble: () => <div data-testid="message-bubble">MessageBubble</div>,
}));

// Mock hooks
vi.mock("@/hooks/useChat", () => ({
  useChat: () => ({
    messages: [],
    sendMessage: vi.fn(),
    createConversation: vi.fn(),
    isLoading: false,
  }),
}));

describe("App", () => {
  it("renders sidebar and input area", () => {
    render(<App />);

    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("input-bar")).toBeInTheDocument();
  });

  it("has correct layout classes", () => {
    const { container } = render(<App />);
    // Check for flex layout classes based on Layout component
    // Layout wrapper has: flex h-screen ...
    expect(container.firstChild).toHaveClass(
      "flex",
      "h-screen",
      "overflow-hidden",
    );
  });
});
