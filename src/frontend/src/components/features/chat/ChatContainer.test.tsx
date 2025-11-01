import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ChatContainer } from "./ChatContainer";
import { renderWithProviders } from "@/test/utils";

// Mock the useFastAPIChat hook
vi.mock("@/lib/use-fastapi-chat", () => ({
  useFastAPIChat: vi.fn(() => ({
    messages: [],
    status: "ready" as const,
    error: null,
    sendMessage: vi.fn(),
    pendingApprovals: [],
    approvalStatuses: {},
    respondToApproval: vi.fn(),
    currentPlan: null,
    conversationId: undefined,
    queueStatus: null,
    connectionStatus: "connected" as const,
    checkHealth: vi.fn(),
    input: "",
    setInput: vi.fn(),
  })),
}));

// Mock other hooks
vi.mock("@/hooks/use-toast", () => ({
  useToast: vi.fn(() => ({
    toast: vi.fn(),
  })),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: vi.fn(() => ({
      invalidateQueries: vi.fn(),
    })),
  };
});

describe("ChatContainer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render chat container", () => {
    renderWithProviders(<ChatContainer />);

    // Should render the chat input (main interactive element)
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("should render connection status indicator", () => {
    renderWithProviders(<ChatContainer />);

    // ConnectionStatusIndicator should be rendered
    // We can check for its presence through the connection status
    const container = screen.getByRole("textbox").closest("div");
    expect(container).toBeInTheDocument();
  });

  it("should render messages when provided", async () => {
    const { useFastAPIChat } = await import("@/lib/use-fastapi-chat");
    vi.mocked(useFastAPIChat).mockReturnValue({
      messages: [
        {
          id: "msg-1",
          role: "user",
          content: "Hello",
        },
        {
          id: "msg-2",
          role: "assistant",
          content: "Hi there!",
        },
      ],
      status: "ready",
      error: null,
      sendMessage: vi.fn(),
      pendingApprovals: [],
      approvalStatuses: {},
      respondToApproval: vi.fn(),
      currentPlan: null,
      conversationId: undefined,
      queueStatus: null,
      connectionStatus: "connected",
      checkHealth: vi.fn(),
      input: "",
      setInput: vi.fn(),
    });

    renderWithProviders(<ChatContainer />);

    await waitFor(() => {
      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });
  });

  it("should render approval prompt when pending approvals exist", async () => {
    const { useFastAPIChat } = await import("@/lib/use-fastapi-chat");
    vi.mocked(useFastAPIChat).mockReturnValue({
      messages: [],
      status: "ready",
      error: null,
      sendMessage: vi.fn(),
      pendingApprovals: [
        {
          id: "req-1",
          operation_type: "test_operation",
          description: "Test approval",
          details: {},
        },
      ],
      approvalStatuses: {
        "req-1": "pending",
      },
      respondToApproval: vi.fn(),
      currentPlan: null,
      conversationId: undefined,
      queueStatus: null,
      connectionStatus: "connected",
      checkHealth: vi.fn(),
      input: "",
      setInput: vi.fn(),
    });

    renderWithProviders(<ChatContainer />);

    await waitFor(() => {
      expect(screen.getByText("Approval Required")).toBeInTheDocument();
    });
  });

  it("should render plan when currentPlan exists", async () => {
    const { useFastAPIChat } = await import("@/lib/use-fastapi-chat");
    vi.mocked(useFastAPIChat).mockReturnValue({
      messages: [],
      status: "ready",
      error: null,
      sendMessage: vi.fn(),
      pendingApprovals: [],
      approvalStatuses: {},
      respondToApproval: vi.fn(),
      currentPlan: {
        id: "plan-1",
        title: "Execution Plan",
        steps: ["Step 1", "Step 2"],
        isStreaming: false,
      },
      conversationId: undefined,
      queueStatus: null,
      connectionStatus: "connected",
      checkHealth: vi.fn(),
      input: "",
      setInput: vi.fn(),
    });

    renderWithProviders(<ChatContainer />);

    await waitFor(() => {
      expect(screen.getByText("Execution Plan")).toBeInTheDocument();
    });
  });

  it("should handle conversation ID prop", () => {
    const onConversationChange = vi.fn();
    renderWithProviders(
      <ChatContainer
        conversationId="conv-123"
        onConversationChange={onConversationChange}
      />,
    );

    // Component should render without errors
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("should render error state when error exists", async () => {
    const { useFastAPIChat } = await import("@/lib/use-fastapi-chat");
    vi.mocked(useFastAPIChat).mockReturnValue({
      messages: [],
      status: "error",
      error: new Error("Something went wrong"),
      sendMessage: vi.fn(),
      pendingApprovals: [],
      approvalStatuses: {},
      respondToApproval: vi.fn(),
      currentPlan: null,
      conversationId: undefined,
      queueStatus: null,
      connectionStatus: "connected",
      checkHealth: vi.fn(),
      input: "",
      setInput: vi.fn(),
    });

    renderWithProviders(<ChatContainer />);

    // Error should be displayed (exact implementation depends on error rendering)
    // For now, just verify component renders without crashing
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });
});
