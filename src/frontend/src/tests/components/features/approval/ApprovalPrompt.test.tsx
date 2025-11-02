import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalPrompt } from "@/components/features/approval/ApprovalPrompt";

describe("ApprovalPrompt", () => {
  const defaultProps = {
    requestId: "req-123",
    status: { status: "pending" as const },
    onApprove: vi.fn(),
    onReject: vi.fn(),
  };

  it("should render approval prompt", () => {
    render(<ApprovalPrompt {...defaultProps} />);

    expect(screen.getByText("Approval Required")).toBeInTheDocument();
    expect(screen.getByText("req-123")).toBeInTheDocument();
  });

  it("should render operation name when provided", () => {
    render(<ApprovalPrompt {...defaultProps} operation="test_operation" />);

    expect(screen.getByText("test_operation")).toBeInTheDocument();
  });

  it("should render function call name when provided", () => {
    render(
      <ApprovalPrompt
        {...defaultProps}
        functionCall={{
          id: "func-1",
          name: "execute_code",
          arguments: { code: "print('hello')" },
        }}
      />,
    );

    expect(screen.getByText("execute_code")).toBeInTheDocument();
  });

  it("should render code when provided", () => {
    render(<ApprovalPrompt {...defaultProps} code="print('hello world')" />);

    const textarea = screen.getByDisplayValue("print('hello world')");
    expect(textarea).toBeInTheDocument();
  });

  it("should render context when provided", () => {
    render(
      <ApprovalPrompt
        {...defaultProps}
        context="This operation will modify the database"
      />,
    );

    expect(
      screen.getByText("This operation will modify the database"),
    ).toBeInTheDocument();
  });

  it("should render risk level badge", () => {
    const { rerender } = render(
      <ApprovalPrompt {...defaultProps} riskLevel="low" />,
    );

    expect(screen.getByText("LOW RISK")).toBeInTheDocument();

    rerender(<ApprovalPrompt {...defaultProps} riskLevel="high" />);

    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
  });

  it("should call onApprove when approve button is clicked", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();

    render(<ApprovalPrompt {...defaultProps} onApprove={onApprove} />);

    const approveButton = screen.getByRole("button", { name: /approve/i });
    await user.click(approveButton);

    expect(onApprove).toHaveBeenCalled();
  });

  it("should call onReject when reject button is clicked with reason", async () => {
    const user = userEvent.setup();
    const onReject = vi.fn();

    render(<ApprovalPrompt {...defaultProps} onReject={onReject} />);

    const reasonTextarea = screen.getByPlaceholderText(/add optional context/i);
    await user.type(reasonTextarea, "Not safe to execute");

    const rejectButton = screen.getByRole("button", { name: /reject/i });
    await user.click(rejectButton);

    expect(onReject).toHaveBeenCalledWith("Not safe to execute");
  });

  it("should require reason for rejection", async () => {
    const user = userEvent.setup();
    const onReject = vi.fn();

    render(<ApprovalPrompt {...defaultProps} onReject={onReject} />);

    const rejectButton = screen.getByRole("button", { name: /reject/i });
    await user.click(rejectButton);

    expect(onReject).not.toHaveBeenCalled();
    expect(screen.getByText(/please provide a reason/i)).toBeInTheDocument();
  });

  it("should show error message when status is error", () => {
    render(
      <ApprovalPrompt
        {...defaultProps}
        status={{ status: "error" as const, error: "Failed to submit" }}
      />,
    );

    expect(screen.getByText(/error:/i)).toBeInTheDocument();
    expect(screen.getByText("Failed to submit")).toBeInTheDocument();
  });

  it("should disable buttons when submitting", () => {
    render(
      <ApprovalPrompt
        {...defaultProps}
        status={{ status: "submitting" as const }}
      />,
    );

    const approveButton = screen.getByRole("button", { name: /submitting/i });
    const rejectButton = screen.getByRole("button", { name: /submitting/i });

    expect(approveButton).toBeDisabled();
    expect(rejectButton).toBeDisabled();
  });

  it("should allow code modification", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();

    render(
      <ApprovalPrompt
        {...defaultProps}
        code="original code"
        onApprove={onApprove}
      />,
    );

    const codeTextarea = screen.getByDisplayValue("original code");
    await user.clear(codeTextarea);
    await user.type(codeTextarea, "modified code");

    const approveButton = screen.getByRole("button", { name: /approve/i });
    await user.click(approveButton);

    expect(onApprove).toHaveBeenCalledWith({
      modifiedCode: "modified code",
    });
  });

  it("should allow parameter modification", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();

    render(
      <ApprovalPrompt
        {...defaultProps}
        functionCall={{
          id: "func-1",
          name: "test_func",
          arguments: { param1: "value1" },
        }}
        onApprove={onApprove}
      />,
    );

    const modifyButton = screen.getByRole("button", { name: /modify/i });
    await user.click(modifyButton);

    const paramsTextarea = screen.getByDisplayValue(/param1/i);
    await user.clear(paramsTextarea);
    await user.type(paramsTextarea, '{"param1": "modified"}');

    const approveButton = screen.getByRole("button", { name: /approve/i });
    await user.click(approveButton);

    expect(onApprove).toHaveBeenCalledWith(
      expect.objectContaining({
        modifiedParams: { param1: "modified" },
      }),
    );
  });
});
