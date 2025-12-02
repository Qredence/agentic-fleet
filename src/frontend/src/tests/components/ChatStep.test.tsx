import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ChatStep } from "../../components/ChatStep";
import type { ConversationStep } from "../../api/types";

describe("ChatStep", () => {
  it("renders thought step correctly", () => {
    const step: ConversationStep = {
      id: "1",
      type: "thought",
      content: "Thinking about it...",
      timestamp: new Date().toISOString(),
    };

    render(<ChatStep step={step} />);
    expect(screen.getByText("Thinking about it...")).toBeInTheDocument();
  });

  it("renders agent_start step correctly", () => {
    const step: ConversationStep = {
      id: "2",
      type: "agent_start",
      content: "Agent started",
      timestamp: new Date().toISOString(),
    };

    render(<ChatStep step={step} />);
    expect(screen.getByText("Agent started")).toBeInTheDocument();
    // Check for yellow color class
    const container = screen.getByText("Agent started").parentElement;
    expect(container).toHaveClass("text-yellow-400");
  });

  it("renders agent_complete step correctly", () => {
    const step: ConversationStep = {
      id: "3",
      type: "agent_complete",
      content: "Agent finished",
      timestamp: new Date().toISOString(),
    };

    render(<ChatStep step={step} />);
    expect(screen.getByText("Agent finished")).toBeInTheDocument();
    const container = screen.getByText("Agent finished").parentElement;
    expect(container).toHaveClass("text-green-400");
  });

  it("renders agent_output step correctly", () => {
    const step: ConversationStep = {
      id: "4",
      type: "agent_output",
      content: "Here is the result",
      timestamp: new Date().toISOString(),
    };

    render(<ChatStep step={step} />);
    expect(screen.getByText("Here is the result")).toBeInTheDocument();
    const container = screen.getByText("Here is the result").parentElement;
    expect(container).toHaveClass("text-purple-400");
  });

  it("expands details when clicked", () => {
    const step: ConversationStep = {
      id: "5",
      type: "thought",
      content: "Click me",
      timestamp: new Date().toISOString(),
      data: { detail: "hidden info" },
    };

    render(<ChatStep step={step} />);

    // Details should not be visible initially
    expect(
      screen.queryByText(/"detail": "hidden info"/),
    ).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText("Click me"));

    // Details should be visible now
    expect(screen.getByText(/"detail": "hidden info"/)).toBeInTheDocument();
  });
});
