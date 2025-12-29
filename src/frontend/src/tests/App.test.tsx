import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders as render } from "@/tests/utils/render";
import App from "@/app/App";

type MockChatStoreState = {
  messages: unknown[];
  conversationId: string | null;
  activeView: "chat" | "dashboard";
  showTrace: boolean;
  showRawReasoning: boolean;
  isLoading: boolean;
  isInitializing: boolean;
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  currentAgent: string | null;
  completedPhases: string[];
  sendMessage: ReturnType<typeof vi.fn>;
  createConversation: ReturnType<typeof vi.fn>;
  cancelStreaming: ReturnType<typeof vi.fn>;
  selectConversation: ReturnType<typeof vi.fn>;
  setActiveView: ReturnType<typeof vi.fn>;
  setShowTrace: ReturnType<typeof vi.fn>;
  setShowRawReasoning: ReturnType<typeof vi.fn>;
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
    conversationId: null,
    activeView: "chat",
    showTrace: true,
    showRawReasoning: false,
    isLoading: false,
    isInitializing: false,
    currentReasoning: "",
    isReasoningStreaming: false,
    currentWorkflowPhase: "",
    currentAgent: null,
    completedPhases: [],
    sendMessage: vi.fn(),
    createConversation: vi.fn(),
    cancelStreaming: vi.fn(),
    selectConversation: vi.fn(),
    setActiveView: vi.fn(),
    setShowTrace: vi.fn(),
    setShowRawReasoning: vi.fn(),
  };
});

describe("App", () => {
  it("renders sidebar and input area", async () => {
    render(<App />);

    await waitFor(
      () => {
        expect(
          screen.getByRole("button", { name: /(start new chat|new chat)/i }),
        ).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
    expect(screen.getByPlaceholderText("Ask anything...")).toBeInTheDocument();
  });

  it("mounts the app with proper structure", async () => {
    const { container } = render(<App />);

    // Assert the UI mounted with proper structure
    await waitFor(
      () => {
        expect(container.querySelector("main.flex.h-screen")).toBeTruthy();
      },
      { timeout: 5000 },
    );
  });
});
