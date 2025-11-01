import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatMessage } from "./ChatMessage";

describe("ChatMessage", () => {
  it("should render user message", () => {
    render(
      <ChatMessage message="Hello world" agent="user" timestamp="12:00 PM" />,
    );

    expect(screen.getByText("Hello world")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("12:00 PM")).toBeInTheDocument();
  });

  it("should render assistant message", () => {
    render(
      <ChatMessage message="Hi there!" agent="analyst" timestamp="12:01 PM" />,
    );

    expect(screen.getByText("Hi there!")).toBeInTheDocument();
    expect(screen.getByText("Data Analyst")).toBeInTheDocument();
    expect(screen.getByText("12:01 PM")).toBeInTheDocument();
  });

  it("should render reasoning when provided", () => {
    render(
      <ChatMessage
        message="Response"
        agent="analyst"
        timestamp="12:00 PM"
        reasoning="I'm thinking about this..."
      />,
    );

    expect(screen.getByText(/Reasoning/i)).toBeInTheDocument();

    // Click to expand
    const reasoningButton = screen.getByText(/Reasoning/i);
    fireEvent.click(reasoningButton);

    expect(screen.getByText(/Data Analyst is thinking/i)).toBeInTheDocument();
    expect(screen.getByText("I'm thinking about this...")).toBeInTheDocument();
  });

  it("should render steps when provided", () => {
    const steps = [
      { label: "Step 1", status: "complete" as const },
      { label: "Step 2", status: "current" as const },
      { label: "Step 3", status: "pending" as const },
    ];

    render(
      <ChatMessage
        message="Response"
        agent="analyst"
        timestamp="12:00 PM"
        steps={steps}
      />,
    );

    expect(screen.getByText("Step 1")).toBeInTheDocument();
    expect(screen.getByText("Step 2")).toBeInTheDocument();
    expect(screen.getByText("Step 3")).toBeInTheDocument();
  });

  it("should render tools when provided", () => {
    const tools = [
      {
        name: "search",
        status: "complete" as const,
        description: "Search completed",
      },
      {
        name: "analyze",
        status: "running" as const,
        description: "Analyzing...",
      },
    ];

    render(
      <ChatMessage
        message="Response"
        agent="analyst"
        timestamp="12:00 PM"
        tools={tools}
      />,
    );

    expect(screen.getByText("search")).toBeInTheDocument();
    expect(screen.getByText("Search completed")).toBeInTheDocument();
    expect(screen.getByText("analyze")).toBeInTheDocument();
    expect(screen.getByText("Analyzing...")).toBeInTheDocument();
  });

  it("should apply streaming animation when isStreaming is true", () => {
    const { container } = render(
      <ChatMessage
        message="Streaming..."
        agent="analyst"
        timestamp="12:00 PM"
        isStreaming={true}
      />,
    );

    const messageElement = container.querySelector(".animate-pulse-subtle");
    expect(messageElement).toBeInTheDocument();
  });

  it("should apply fade-in animation when isNew is true", () => {
    const { container } = render(
      <ChatMessage
        message="New message"
        agent="analyst"
        timestamp="12:00 PM"
        isNew={true}
      />,
    );

    const messageElement = container.querySelector(".animate-fade-in");
    expect(messageElement).toBeInTheDocument();
  });
});
