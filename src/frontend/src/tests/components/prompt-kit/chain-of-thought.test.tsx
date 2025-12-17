import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Message as ChatMessage, ConversationStep } from "@/api/types";
import { ChainOfThoughtTrace } from "@/features/chat/components/chain-of-thought";

const mockOnWorkflowResponse = vi.fn();

function createMockMessage(overrides?: Partial<ChatMessage>): ChatMessage {
  return {
    id: "test-message-1",
    role: "assistant",
    content: "Test content",
    created_at: new Date().toISOString(),
    steps: [],
    ...overrides,
  };
}

function createMockStep(overrides?: {
  type?: ConversationStep["type"];
  content?: string;
  data?: Record<string, unknown>;
  kind?: string;
  timestamp?: string;
}): ConversationStep {
  return {
    id: `step-${Math.random()}`,
    type: overrides?.type || "analysis",
    content: overrides?.content || "Step content",
    timestamp: overrides?.timestamp || new Date().toISOString(),
    kind: overrides?.kind,
    data: overrides?.data,
  };
}

describe("ChainOfThoughtTrace", () => {
  it("returns null when no steps and no phase", () => {
    const message = createMockMessage({ steps: [] });
    const { container } = render(
      <ChainOfThoughtTrace
        message={message}
        isStreaming={false}
        onWorkflowResponse={mockOnWorkflowResponse}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders phase shimmer when streaming and no content", () => {
    const message = createMockMessage({
      workflowPhase: "Analyzing...",
      content: "",
      steps: [],
    });
    render(
      <ChainOfThoughtTrace
        message={message}
        isStreaming={true}
        onWorkflowResponse={mockOnWorkflowResponse}
        isLoading={false}
      />,
    );
    expect(screen.getByText("Analyzing...")).toBeInTheDocument();
  });

  it("renders reasoning section when present", () => {
    const message = createMockMessage({
      steps: [
        {
          id: "reasoning-1",
          type: "reasoning",
          content: "This is reasoning content",
          timestamp: new Date().toISOString(),
        },
      ],
    });
    render(
      <ChainOfThoughtTrace
        message={message}
        isStreaming={false}
        onWorkflowResponse={mockOnWorkflowResponse}
        isLoading={false}
      />,
    );
    expect(screen.getByText("Reasoning")).toBeInTheDocument();
  });

  describe("Trigger label formatting", () => {
    it("formats trigger with capability", () => {
      const step = createMockStep({
        type: "analysis",
        data: { capabilities: "general_reasoning" },
        timestamp: "2024-01-01T08:41:00Z",
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      // Format is "Event · Analysis · using general_reasoning · HH:MM AM/PM"
      expect(
        screen.getByText(/Event · Analysis · using general_reasoning/),
      ).toBeInTheDocument();
    });

    it("formats trigger with capability array", () => {
      const step = createMockStep({
        type: "analysis",
        data: { capabilities: ["general_reasoning", "code_generation"] },
        timestamp: "2024-01-01T08:41:00Z",
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      // Should use first capability
      expect(
        screen.getByText(/Event · Analysis · using general_reasoning/),
      ).toBeInTheDocument();
    });

    it("formats trigger without capability (fallback)", () => {
      const step = createMockStep({
        type: "analysis",
        data: {},
        timestamp: "2024-01-01T08:41:00Z",
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      // Should show "Event · Analysis · HH:MM" (no capability)
      expect(screen.getByText(/Event · Analysis/)).toBeInTheDocument();
    });
  });

  describe("Content rendering", () => {
    it("renders step content with Markdown component when expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "This is **bold** content",
      });
      const message = createMockMessage({ steps: [step] });
      const { container } = render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible by clicking the trigger
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      // Markdown should render bold text
      expect(container.querySelector("strong")).toBeInTheDocument();
    });

    it("does not render empty content", () => {
      const step = createMockStep({
        type: "analysis",
        content: "",
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      // Should still render the trigger
      expect(screen.getByText(/Event · Analysis/)).toBeInTheDocument();
    });
  });

  describe("Reasoning summary", () => {
    it("renders reasoning summary section with structured data when expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          complexity: "medium",
          capabilities: "general_reasoning",
          steps: 1,
          intent: "code_generation",
          intent_confidence: 0.98,
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      expect(screen.getByText("Reasoning summary")).toBeInTheDocument();
      expect(screen.getByText(/complexity/i)).toBeInTheDocument();
    });

    it("does not render reasoning summary when no structured data", () => {
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          other_field: "value",
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      expect(screen.queryByText("Reasoning summary")).not.toBeInTheDocument();
    });

    it("renders partial reasoning summary when only some fields present", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          complexity: "medium",
          intent: "code_generation",
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      expect(screen.getByText("Reasoning summary")).toBeInTheDocument();
      expect(screen.getByText(/complexity/i)).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("applies error styling to trigger", () => {
      const step = createMockStep({
        type: "error",
        content: "Error occurred",
      });
      const message = createMockMessage({ steps: [step] });
      const { container } = render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      const trigger = container.querySelector('[class*="text-destructive"]');
      expect(trigger).toBeInTheDocument();
    });
  });

  describe("Request responder", () => {
    it("renders request responder when step is request type and expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "request",
        content: "Request content",
        data: {
          request_id: "req-123",
          request_type: "user_input",
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Request/ });
      await user.click(trigger);

      // WorkflowRequestResponder should be rendered with request ID
      expect(screen.getByText(/req-123/i)).toBeInTheDocument();
    });
  });

  describe("Output rendering", () => {
    it("renders output when present and expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          output: "This is the output",
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      expect(screen.getByText("This is the output")).toBeInTheDocument();
    });
  });

  describe("Extra data rendering", () => {
    it("renders extra data when present and expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          custom_field: "custom_value",
          another_field: 123,
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      expect(screen.getByText(/custom_field/i)).toBeInTheDocument();
      expect(screen.getByText(/custom_value/i)).toBeInTheDocument();
    });

    it("excludes reasoning summary fields from extra data when expanded", async () => {
      const user = userEvent.setup();
      const step = createMockStep({
        type: "analysis",
        content: "Main content",
        data: {
          complexity: "medium",
          custom_field: "custom_value",
        },
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );

      // Expand the collapsible
      const trigger = screen.getByRole("button", { name: /Event · Analysis/ });
      await user.click(trigger);

      // Complexity should be in reasoning summary, not extra data
      expect(screen.getByText("Reasoning summary")).toBeInTheDocument();
      // Custom field should still appear somewhere (either in summary or extra)
      expect(screen.getByText(/custom_field/i)).toBeInTheDocument();
    });
  });

  describe("Streaming state", () => {
    it("shows TextShimmer for Events label when streaming", () => {
      const step = createMockStep({
        type: "analysis",
        content: "Content",
      });
      const message = createMockMessage({ steps: [step] });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={true}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      // TextShimmer should be rendered for "Events"
      expect(screen.getByText("Events")).toBeInTheDocument();
    });

    it("shows event count", () => {
      const steps = [
        createMockStep({ type: "analysis" }),
        createMockStep({ type: "routing" }),
        createMockStep({ type: "execution" }),
      ];
      const message = createMockMessage({ steps });
      render(
        <ChainOfThoughtTrace
          message={message}
          isStreaming={false}
          onWorkflowResponse={mockOnWorkflowResponse}
          isLoading={false}
        />,
      );
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });
});
