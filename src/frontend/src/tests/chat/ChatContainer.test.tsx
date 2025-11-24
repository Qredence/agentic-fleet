import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { useChatStore } from "@/stores/chatStore";
import { useStreamingChat } from "@/hooks/useStreamingChat";

// Mock dependencies
vi.mock("@/stores/chatStore");
vi.mock("@/hooks/useStreamingChat");
vi.mock("@/components/chat/MessageList", () => ({
  MessageList: () => <div data-testid="message-list">MessageList</div>,
}));
vi.mock("@/components/chat/PromptInputArea", () => ({
  PromptInputArea: () => (
    <div data-testid="prompt-input-area">PromptInputArea</div>
  ),
}));

describe("ChatContainer", () => {
  const mockCreateConversation = vi.fn();
  const mockAddMessage = vi.fn();
  const mockSendMessage = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementation
    (useChatStore as any).mockReturnValue({
      conversations: [
        {
          id: "123",
          title: "Test Chat",
          messages: [],
        },
      ],
      currentConversationId: "123",
      addMessage: mockAddMessage,
      createConversation: mockCreateConversation,
      setStreamingState: vi.fn(),
      clearStreaming: vi.fn(),
      streamingContent: "",
      streamingAgentId: undefined,
      streamingReasoning: undefined,
    });
    (useStreamingChat as any).mockReturnValue({
      isStreaming: false,
      streamingContent: "",
      orchestratorThought: "",
      currentAgentId: undefined,
      sendMessage: mockSendMessage,
    });
  });

  it("renders chat interface when conversation is selected", () => {
    render(<ChatContainer />);

    expect(screen.getByText("Test Chat")).toBeInTheDocument();
    expect(screen.getByTestId("message-list")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-input-area")).toBeInTheDocument();
  });

  it("renders new conversation state when no conversation is selected", () => {
    (useChatStore as any).mockReturnValue({
      conversations: [],
      currentConversationId: null,
      createConversation: mockCreateConversation,
      addMessage: mockAddMessage,
      setStreamingState: vi.fn(),
      clearStreaming: vi.fn(),
      streamingContent: "",
      streamingAgentId: undefined,
      streamingReasoning: undefined,
    });

    render(<ChatContainer />);

    expect(screen.getByText("New Conversation")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-input-area")).toBeInTheDocument();
  });
});
