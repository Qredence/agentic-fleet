import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/app/App";

type MockChatStoreState = {
  messages: unknown[];
  conversations: unknown[];
  conversationId: string | null;
  activeView: "chat" | "dashboard";
  isLoading: boolean;
  isInitializing: boolean;
  isConversationsLoading: boolean;
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  currentAgent: string | null;
  completedPhases: string[];
  sendMessage: ReturnType<typeof vi.fn>;
  createConversation: ReturnType<typeof vi.fn>;
  cancelStreaming: ReturnType<typeof vi.fn>;
  selectConversation: ReturnType<typeof vi.fn>;
  loadConversations: ReturnType<typeof vi.fn>;
  setActiveView: ReturnType<typeof vi.fn>;
};

let mockStoreState: MockChatStoreState | null = null;

vi.mock("@/features/chat/stores", () => ({
  useChatStore: (
    selector?: (state: MockChatStoreState) => unknown,
    _equalityFn?: unknown,
  ) => {
    if (!mockStoreState) {
      throw new Error("Test misconfiguration: mockStoreState not initialized");
    }
    return typeof selector === "function"
      ? selector(mockStoreState)
      : mockStoreState;
  },
}));

beforeEach(() => {
  mockStoreState = {
    messages: [],
    conversations: [],
    conversationId: null,
    activeView: "chat",
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
  };
});

describe("App", () => {
  it("renders sidebar and input area", () => {
    render(<App />);

    expect(
      screen.getByRole("button", { name: /start new chat/i }),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask anything...")).toBeInTheDocument();
  });

  it("calls loadConversations on mount", async () => {
    const { container } = render(<App />);

    const loadConversations = mockStoreState?.loadConversations;
    await waitFor(() => expect(loadConversations).toHaveBeenCalledTimes(1));

    // Also assert the UI mounted (sanity check).
    expect(container.querySelector("main.flex.h-screen")).toBeTruthy();
  });
});
