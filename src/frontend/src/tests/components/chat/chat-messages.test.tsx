import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderComponent as render } from "@/tests/utils/render";
import { ChatMessages } from "@/components/chat/chat-messages";
import type { Message as ChatMessage } from "@/api/types";

/**
 * Mock scrollIntoView since it's not implemented in jsdom
 */
Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
  value: vi.fn(),
  writable: true,
});

describe("ChatMessages", () => {
  const mockMessages: ChatMessage[] = [
    {
      id: "msg-1",
      role: "user",
      content: "Hello there!",
      created_at: Date.now(),
    },
    {
      id: "msg-2",
      role: "assistant",
      content: "Hi! How can I help you today?",
      created_at: Date.now() + 1000,
    },
    {
      id: "msg-3",
      role: "assistant",
      content: "I'm here to assist with your questions.",
      created_at: Date.now() + 2000,
    },
  ];

  it("renders user messages correctly", () => {
    const userMessages = mockMessages.filter((msg) => msg.role === "user");
    render(<ChatMessages messages={userMessages} rootClassName="test-root" />);

    // Should render user messages
    const message = screen.getByText("Hello there!");
    expect(message).toBeInTheDocument();

    // User messages are right-aligned (wrapped in a div with justify-end)
    const messageWrapper = message.parentElement?.parentElement;
    expect(messageWrapper).toHaveClass("justify-end");
  });

  it("renders assistant messages correctly", () => {
    const assistantMessages = mockMessages.filter(
      (msg) => msg.role === "assistant",
    );
    render(<ChatMessages messages={assistantMessages} />);

    // Should render assistant messages
    expect(
      screen.getByText("Hi! How can I help you today?"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I'm here to assist with your questions."),
    ).toBeInTheDocument();

    // Assistant messages should have copy button
    const copyButtons = screen.getAllByRole("button", { name: /copy/i });
    expect(copyButtons).toHaveLength(2);
  });

  it("displays streaming indicator for last assistant message when loading", () => {
    const messages = [
      ...mockMessages,
      {
        id: "msg-streaming",
        role: "assistant",
        content: "Streaming response",
        created_at: Date.now() + 3000,
      },
    ];

    render(<ChatMessages messages={messages} isLoading={true} />);

    // Last message should show streaming content with whitespace-pre-wrap
    // The text is inside a <p> rendered by Markdown, so we need to check its container
    const lastMessage = screen.getByText("Streaming response");
    const messageContainer = lastMessage.closest(".whitespace-pre-wrap");
    expect(messageContainer).toBeInTheDocument();
    // Note: streamdown handles cursor rendering internally, so we don't manually add "▍"
  });

  it("calls onCopy when copy button is clicked", async () => {
    const user = userEvent.setup();
    const mockOnCopy = vi.fn();

    const assistantMessages = mockMessages.filter(
      (msg) => msg.role === "assistant",
    );
    render(<ChatMessages messages={assistantMessages} onCopy={mockOnCopy} />);

    // Click the first copy button
    const copyButtons = screen.getAllByRole("button", { name: /copy/i });
    await user.click(copyButtons[0]);

    expect(mockOnCopy).toHaveBeenCalledTimes(1);
    expect(mockOnCopy).toHaveBeenCalledWith("Hi! How can I help you today?");
  });

  it("uses default clipboard copy when onCopy prop is not provided", async () => {
    const user = userEvent.setup();
    const writeTextSpy = vi
      .spyOn(navigator.clipboard, "writeText")
      .mockResolvedValue();

    const assistantMessages = mockMessages.filter(
      (msg) => msg.role === "assistant",
    );
    render(<ChatMessages messages={assistantMessages} />);

    // Click the first copy button
    const copyButtons = screen.getAllByRole("button", { name: /copy/i });
    await user.click(copyButtons[0]);

    expect(writeTextSpy).toHaveBeenCalledTimes(1);
    expect(writeTextSpy).toHaveBeenCalledWith("Hi! How can I help you today?");

    writeTextSpy.mockRestore();
  });

  it("does not show copy button for user messages", () => {
    const userMessages = mockMessages.filter((msg) => msg.role === "user");
    render(<ChatMessages messages={userMessages} />);

    // Should not have copy buttons for user messages
    expect(
      screen.queryByRole("button", { name: /copy/i }),
    ).not.toBeInTheDocument();
  });

  it("handles empty messages array", () => {
    const { container } = render(<ChatMessages messages={[]} />);

    // Should render container but no messages
    expect(container.firstChild).toBeInTheDocument();

    // Message list should be empty
    const messageElements = container.querySelectorAll(
      '[data-testid="message"]',
    );
    expect(messageElements).toHaveLength(0);
  });

  it("applies custom root class name", () => {
    const { container } = render(
      <ChatMessages
        messages={mockMessages}
        rootClassName="custom-root-class"
      />,
    );

    const rootElement = container.firstChild;
    expect(rootElement).toHaveClass("custom-root-class");
  });

  it("applies custom content class name", () => {
    const { container } = render(
      <ChatMessages
        messages={mockMessages}
        contentClassName="custom-content-class"
      />,
    );

    // The contentClassName is applied to ChatContainerContent
    // which renders a StickToBottom.Content component
    const contentElement = container.querySelector(".custom-content-class");
    expect(contentElement).toBeInTheDocument();
    expect(contentElement).toHaveClass("custom-content-class");
  });

  it("renders trace component when renderTrace prop is provided", () => {
    const mockRenderTrace = vi.fn(() => (
      <div data-testid="trace">Trace Info</div>
    ));

    // Add steps to messages so renderTrace gets called
    const messagesWithSteps = mockMessages.map((msg) =>
      msg.role === "assistant" ? { ...msg, steps: [{ id: "1" }] } : msg,
    );

    render(
      <ChatMessages
        messages={messagesWithSteps}
        renderTrace={mockRenderTrace}
      />,
    );

    expect(mockRenderTrace).toHaveBeenCalledTimes(
      messagesWithSteps.filter((m) => m.role === "assistant").length,
    );
    expect(screen.getAllByTestId("trace")).toHaveLength(2); // Two assistant messages
  });

  it("handles message content that is not a string", () => {
    const messagesWithObjectContent: ChatMessage[] = [
      {
        id: "msg-object",
        role: "assistant",
        content: {
          type: "error",
          message: "Something went wrong",
        } as unknown as string,
        created_at: Date.now(),
      },
    ];

    render(<ChatMessages messages={messagesWithObjectContent} />);

    // Should render JSON stringified content
    expect(screen.getByText(/type.*error/i)).toBeInTheDocument();
    expect(
      screen.getByText(/message.*Something went wrong/i),
    ).toBeInTheDocument();
  });
});
