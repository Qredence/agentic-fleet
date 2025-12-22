/**
 * Markdown Component Tests
 *
 * Tests for the Markdown component that uses streamdown for rendering.
 */

import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders as render } from "@/tests/utils/render";
import { Markdown } from "@/components/message/markdown";

describe("Markdown", () => {
  describe("basic rendering", () => {
    it("renders plain text", () => {
      render(<Markdown>Hello, world!</Markdown>);
      expect(screen.getByText("Hello, world!")).toBeInTheDocument();
    });

    it("renders bold text", () => {
      render(<Markdown>This is **bold** text</Markdown>);
      // Streamdown may render bold differently, check for presence
      expect(screen.getByText(/bold/)).toBeInTheDocument();
    });

    it("renders italic text", () => {
      render(<Markdown>This is *italic* text</Markdown>);
      const italicElement = screen.getByText("italic");
      expect(italicElement.tagName).toBe("EM");
    });

    it("renders headings", () => {
      render(<Markdown># Heading 1</Markdown>);
      const heading = screen.getByRole("heading", { level: 1 });
      expect(heading).toHaveTextContent("Heading 1");
    });

    it("renders links", () => {
      render(<Markdown>[Click here](https://example.com)</Markdown>);
      const link = screen.getByRole("link");
      // URL may have trailing slash added by the renderer
      expect(link.getAttribute("href")).toContain("example.com");
      expect(link).toHaveTextContent("Click here");
    });

    it("renders lists", () => {
      render(
        <Markdown>
          {`- Item 1
- Item 2
- Item 3`}
        </Markdown>,
      );
      const listItems = screen.getAllByRole("listitem");
      expect(listItems).toHaveLength(3);
    });
  });

  describe("code rendering", () => {
    it("renders inline code with styling", () => {
      render(<Markdown>Use the `console.log()` function</Markdown>);
      const codeElement = screen.getByText("console.log()");
      expect(codeElement.tagName).toBe("SPAN");
      expect(codeElement).toHaveClass("font-mono");
    });

    it("renders code blocks", () => {
      const codeContent = `\`\`\`javascript
const x = 1;
\`\`\``;
      render(<Markdown>{codeContent}</Markdown>);

      // Code block should be rendered
      expect(screen.getByText(/const x = 1/)).toBeInTheDocument();
    });

    it("renders plaintext code blocks without language", () => {
      const codeContent = `\`\`\`
plain text here
\`\`\``;
      render(<Markdown>{codeContent}</Markdown>);

      expect(screen.getByText(/plain text here/)).toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("applies custom className", () => {
      render(<Markdown className="custom-class">Content</Markdown>);
      // Find the element with custom-class within the rendered output
      const element = document.querySelector(".custom-class");
      expect(element).toBeInTheDocument();
    });

    it("renders with prose styling when used in MessageContent", () => {
      render(<Markdown className="prose">Prose content</Markdown>);
      const element = screen.getByText("Prose content").closest(".prose");
      expect(element).toBeInTheDocument();
    });
  });

  describe("edge cases", () => {
    it("handles empty string", () => {
      const { container } = render(<Markdown>{""}</Markdown>);
      expect(container.firstChild).toBeInTheDocument();
    });

    it("handles multiline content", () => {
      render(
        <Markdown>
          {`Line 1

Line 2

Line 3`}
        </Markdown>,
      );
      expect(screen.getByText("Line 1")).toBeInTheDocument();
      expect(screen.getByText("Line 2")).toBeInTheDocument();
      expect(screen.getByText("Line 3")).toBeInTheDocument();
    });

    it("handles special characters", () => {
      render(<Markdown>{"Special: <>&\"'"}</Markdown>);
      expect(screen.getByText(/Special:/)).toBeInTheDocument();
    });

    it("handles GFM tables", () => {
      render(
        <Markdown>
          {`| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |`}
        </Markdown>,
      );
      expect(screen.getByText("Header 1")).toBeInTheDocument();
      expect(screen.getByText("Cell 1")).toBeInTheDocument();
    });
  });
});
