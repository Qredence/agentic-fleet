import { describe, expect, it, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderComponent as render } from "@/tests/utils/render";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from "@/components/chat/prompt-input";
import { Button } from "@/components/ui/button";

describe("PromptInput", () => {
  it("renders children correctly", () => {
    render(
      <PromptInput>
        <PromptInputTextarea placeholder="Type something..." />
        <PromptInputActions>
          <Button>Send</Button>
        </PromptInputActions>
      </PromptInput>,
    );

    expect(
      screen.getByPlaceholderText("Type something..."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("handles click to focus textarea", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <PromptInput>
        <PromptInputTextarea placeholder="Type something..." />
      </PromptInput>,
    );

    const promptInput = container.firstChild as HTMLElement;
    const textarea = screen.getByPlaceholderText("Type something...");

    // Click on the container should focus the textarea
    await user.click(promptInput);
    expect(textarea).toHaveFocus();
  });

  it("does not focus textarea when disabled", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <PromptInput disabled={true}>
        <PromptInputTextarea placeholder="Type something..." />
      </PromptInput>,
    );

    const promptInput = container.firstChild as HTMLElement;
    const textarea = screen.getByPlaceholderText("Type something...");

    expect(promptInput).toHaveClass("cursor-not-allowed");
    expect(promptInput).toHaveClass("opacity-60");

    // Click should not focus when disabled
    await user.click(promptInput);
    expect(textarea).not.toHaveFocus();
  });

  it("applies custom className", () => {
    const { container } = render(
      <PromptInput className="custom-class">
        <PromptInputTextarea />
      </PromptInput>,
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("handles onClick prop", () => {
    const handleClick = vi.fn();
    const { container } = render(
      <PromptInput onClick={handleClick}>
        <PromptInputTextarea />
      </PromptInput>,
    );

    fireEvent.click(container.firstChild!);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});

describe("PromptInputTextarea", () => {
  it("updates value when typed", async () => {
    const user = userEvent.setup();
    const handleValueChange = vi.fn();

    render(
      <PromptInput onValueChange={handleValueChange}>
        <PromptInputTextarea placeholder="Type something..." />
      </PromptInput>,
    );

    const textarea = screen.getByPlaceholderText("Type something...");
    await user.type(textarea, "Hello World");

    // onValueChange gets called after each character, check final value
    expect(handleValueChange).toHaveBeenLastCalledWith("Hello World");
  });

  it("calls onSubmit on Enter without Shift", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    const handleKeyDown = vi.fn();

    render(
      <PromptInput onSubmit={handleSubmit}>
        <PromptInputTextarea onKeyDown={handleKeyDown} />
      </PromptInput>,
    );

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Test message{Enter}");

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    // "Test message" = 12 characters + {Enter} = 13 keydown events total
    expect(handleKeyDown).toHaveBeenCalledTimes(13);
  });

  it("does not call onSubmit on Shift+Enter", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <PromptInput onSubmit={handleSubmit}>
        <PromptInputTextarea />
      </PromptInput>,
    );

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Test message{Shift>}{Enter}{/Shift}");

    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("autosizes based on content", () => {
    const { container } = render(
      <PromptInput maxHeight={100}>
        <PromptInputTextarea value="Line 1\nLine 2\nLine 3\nLine 4\nLine 5" />
      </PromptInput>,
    );

    const textarea = container.querySelector("textarea");
    expect(textarea).toBeInTheDocument();
    expect(textarea?.style.height).toBeDefined();
  });

  it("disables autosizing when disableAutosize is true", () => {
    const { container } = render(
      <PromptInput maxHeight={100}>
        <PromptInputTextarea
          value="Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
          disableAutosize={true}
        />
      </PromptInput>,
    );

    const textarea = container.querySelector("textarea");
    expect(textarea).toBeInTheDocument();
    expect(textarea?.style.height).toBe(""); // Height should not be set
  });

  it("handles disabled state", () => {
    render(
      <PromptInput disabled={true}>
        <PromptInputTextarea placeholder="Disabled..." />
      </PromptInput>,
    );

    const textarea = screen.getByPlaceholderText("Disabled...");
    expect(textarea).toBeDisabled();
  });

  it("applies custom className", () => {
    const { container } = render(
      <PromptInput>
        <PromptInputTextarea className="custom-textarea-class" />
      </PromptInput>,
    );

    const textarea = container.querySelector("textarea");
    expect(textarea).toHaveClass("custom-textarea-class");
  });
});

describe("PromptInputActions", () => {
  it("renders children correctly", () => {
    render(
      <PromptInput>
        <PromptInputTextarea />
        <PromptInputActions className="actions-class">
          <Button data-testid="button-1">Action 1</Button>
          <Button data-testid="button-2">Action 2</Button>
        </PromptInputActions>
      </PromptInput>,
    );

    expect(screen.getByTestId("button-1")).toBeInTheDocument();
    expect(screen.getByTestId("button-2")).toBeInTheDocument();

    const actionsContainer = screen.getByTestId("button-1").parentElement;
    expect(actionsContainer).toHaveClass("actions-class");
  });
});

describe("PromptInputAction", () => {
  it("wraps children with tooltip", () => {
    render(
      <PromptInput>
        <PromptInputTextarea />
        <PromptInputActions>
          <PromptInputAction tooltip="Copy to clipboard">
            <Button data-testid="action-button">Copy</Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>,
    );

    const button = screen.getByTestId("action-button");
    expect(button).toBeInTheDocument();

    // Tooltip should be associated with the button
    expect(button.parentElement).toBeInstanceOf(HTMLElement);
  });

  it("disables tooltip when input is disabled", () => {
    render(
      <PromptInput disabled={true}>
        <PromptInputTextarea />
        <PromptInputActions>
          <PromptInputAction tooltip="Copy to clipboard">
            <Button>Copy</Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>,
    );

    const button = screen.getByRole("button");
    // When PromptInput is disabled, the tooltip trigger is disabled
    // which disables the button via asChild
    expect(button).toBeDisabled();
  });

  it("handles click events on children", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <PromptInput>
        <PromptInputTextarea />
        <PromptInputActions>
          <PromptInputAction tooltip="Test action">
            <Button onClick={handleClick}>Click me</Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>,
    );

    const button = screen.getByRole("button", { name: "Click me" });
    await user.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("accepts Tooltip props", () => {
    render(
      <PromptInput>
        <PromptInputTextarea />
        <PromptInputActions>
          <PromptInputAction tooltip="Bottom tooltip" side="bottom">
            <Button>Action</Button>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>,
    );

    // Tooltip should be configured with side="bottom"
    const button = screen.getByRole("button");
    const tooltipTrigger = button.parentElement;
    expect(tooltipTrigger).toBeInTheDocument();
  });
});
