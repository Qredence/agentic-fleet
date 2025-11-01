import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatInput } from "./ChatInput";

describe("ChatInput", () => {
  it("should render input field", () => {
    const onSendMessage = vi.fn();
    render(<ChatInput onSendMessage={onSendMessage} />);

    const textarea = screen.getByRole("textbox");
    expect(textarea).toBeInTheDocument();
  });

  it("should call onSendMessage when form is submitted", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn();

    render(<ChatInput onSendMessage={onSendMessage} />);

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Hello world");

    const form = textarea.closest("form");
    expect(form).toBeInTheDocument();

    await user.type(textarea, "{Enter}");

    expect(onSendMessage).toHaveBeenCalledWith("Hello world");
  });

  it("should not call onSendMessage with empty message", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn();

    render(<ChatInput onSendMessage={onSendMessage} />);

    const textarea = screen.getByRole("textbox");
    const form = textarea.closest("form");
    expect(form).toBeInTheDocument();

    await user.type(textarea, "{Enter}");

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it("should clear input after sending message", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn();

    render(<ChatInput onSendMessage={onSendMessage} />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "Hello world");
    await user.type(textarea, "{Enter}");

    expect(textarea.value).toBe("");
  });

  it("should be disabled when disabled prop is true", () => {
    const onSendMessage = vi.fn();
    render(<ChatInput onSendMessage={onSendMessage} disabled={true} />);

    const textarea = screen.getByRole("textbox");
    expect(textarea).toBeDisabled();
  });

  it("should trim whitespace from message", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn();

    render(<ChatInput onSendMessage={onSendMessage} />);

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "  Hello world  ");
    await user.type(textarea, "{Enter}");

    expect(onSendMessage).toHaveBeenCalledWith("Hello world");
  });
});
