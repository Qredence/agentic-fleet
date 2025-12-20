/**
 * Reasoning Component Tests
 *
 * Tests for the Reasoning component (prompt-kit based).
 */

import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "@/tests/utils/render";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "@/components/message/reasoning";

describe("Reasoning", () => {
  describe("basic rendering", () => {
    it("renders trigger and collapsed content", () => {
      render(
        <Reasoning>
          <ReasoningTrigger>Show reasoning</ReasoningTrigger>
          <ReasoningContent>Hidden content</ReasoningContent>
        </Reasoning>,
      );

      expect(screen.getByText("Show reasoning")).toBeInTheDocument();
      // Content should be in DOM but visually hidden (max-height: 0)
      expect(screen.getByText("Hidden content")).toBeInTheDocument();
    });

    it("applies custom className to container", () => {
      const { container } = render(
        <Reasoning className="custom-reasoning">
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      expect(container.firstChild).toHaveClass("custom-reasoning");
    });
  });

  describe("toggle behavior", () => {
    it("expands content when trigger is clicked", async () => {
      const user = userEvent.setup();

      render(
        <Reasoning>
          <ReasoningTrigger>Show reasoning</ReasoningTrigger>
          <ReasoningContent>Expanded content</ReasoningContent>
        </Reasoning>,
      );

      const trigger = screen.getByRole("button");
      await user.click(trigger);

      // After click, content should be visible (max-height > 0)
      const content = screen.getByText("Expanded content");
      await waitFor(() => {
        const parent = content.closest('[class*="overflow-hidden"]');
        expect(parent).toBeInTheDocument();
      });
    });

    it("collapses content when trigger is clicked again", async () => {
      const user = userEvent.setup();

      render(
        <Reasoning>
          <ReasoningTrigger>Toggle</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      const trigger = screen.getByRole("button");

      // Open
      await user.click(trigger);
      // Close
      await user.click(trigger);

      // Content should be collapsed (max-height: 0)
      const content = screen.getByText("Content");
      const parent = content.closest('[class*="overflow-hidden"]');
      expect(parent).toHaveStyle({ maxHeight: "0px" });
    });

    it("rotates chevron icon when expanded", async () => {
      const user = userEvent.setup();

      render(
        <Reasoning>
          <ReasoningTrigger>Toggle</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      const trigger = screen.getByRole("button");
      await user.click(trigger);

      // Find the chevron container (has rotate-180 when open)
      const chevronContainer = trigger.querySelector(
        '[class*="transition-transform"]',
      );
      expect(chevronContainer).toHaveClass("rotate-180");
    });
  });

  describe("controlled mode", () => {
    it("respects controlled open state", () => {
      render(
        <Reasoning open={true}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent>Visible content</ReasoningContent>
        </Reasoning>,
      );

      const content = screen.getByText("Visible content");
      const parent = content.closest('[class*="overflow-hidden"]');
      // Should have non-zero max-height when open
      expect(parent).not.toHaveStyle({ maxHeight: "0px" });
    });

    it("calls onOpenChange when toggled in controlled mode", async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();

      render(
        <Reasoning open={false} onOpenChange={onOpenChange}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      const trigger = screen.getByRole("button");
      await user.click(trigger);

      expect(onOpenChange).toHaveBeenCalledWith(true);
    });
  });

  describe("streaming auto-open behavior", () => {
    it("auto-opens when isStreaming becomes true", async () => {
      const { rerender } = render(
        <Reasoning isStreaming={false}>
          <ReasoningTrigger>Reasoning</ReasoningTrigger>
          <ReasoningContent>Streaming content</ReasoningContent>
        </Reasoning>,
      );

      // Initially closed
      const content = screen.getByText("Streaming content");
      const parent = content.closest('[class*="overflow-hidden"]');
      expect(parent).toHaveStyle({ maxHeight: "0px" });

      // Start streaming
      rerender(
        <Reasoning isStreaming={true}>
          <ReasoningTrigger>Reasoning</ReasoningTrigger>
          <ReasoningContent>Streaming content</ReasoningContent>
        </Reasoning>,
      );

      // Should auto-open
      await waitFor(() => {
        expect(parent).not.toHaveStyle({ maxHeight: "0px" });
      });
    });

    it("auto-closes when isStreaming becomes false", async () => {
      const { rerender } = render(
        <Reasoning isStreaming={true}>
          <ReasoningTrigger>Reasoning</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      // Wait for auto-open
      const content = screen.getByText("Content");
      const parent = content.closest('[class*="overflow-hidden"]');

      await waitFor(() => {
        expect(parent).not.toHaveStyle({ maxHeight: "0px" });
      });

      // Stop streaming
      rerender(
        <Reasoning isStreaming={false}>
          <ReasoningTrigger>Reasoning</ReasoningTrigger>
          <ReasoningContent>Content</ReasoningContent>
        </Reasoning>,
      );

      // Should auto-close
      await waitFor(() => {
        expect(parent).toHaveStyle({ maxHeight: "0px" });
      });
    });
  });

  describe("markdown support", () => {
    it("renders content as markdown when markdown prop is true", () => {
      render(
        <Reasoning open={true}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent markdown>**Bold** text</ReasoningContent>
        </Reasoning>,
      );

      const boldElement = screen.getByText("Bold");
      expect(boldElement.tagName).toBe("STRONG");
    });

    it("renders content as plain text when markdown prop is false", () => {
      render(
        <Reasoning open={true}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent>**Not bold** text</ReasoningContent>
        </Reasoning>,
      );

      expect(screen.getByText("**Not bold** text")).toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("applies contentClassName to inner content", () => {
      render(
        <Reasoning open={true}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent contentClassName="custom-content">
            Styled content
          </ReasoningContent>
        </Reasoning>,
      );

      const content = screen.getByText("Styled content");
      expect(content.closest(".custom-content")).toBeInTheDocument();
    });

    it("applies prose styling to content", () => {
      render(
        <Reasoning open={true}>
          <ReasoningTrigger>Trigger</ReasoningTrigger>
          <ReasoningContent>Prose content</ReasoningContent>
        </Reasoning>,
      );

      const content = screen.getByText("Prose content");
      expect(content.closest(".prose")).toBeInTheDocument();
    });
  });
});
