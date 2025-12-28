/**
 * Markdown Component
 *
 * CUSTOM COMPONENT - Not from shadcn/ui registry.
 *
 * A markdown renderer using Streamdown for streaming markdown support.
 * Integrates with the custom CodeBlock component for syntax highlighting.
 */
import { cn } from "@/lib/utils";
import { memo } from "react";
import type { Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import { Streamdown } from "streamdown";
import {
  CodeBlock,
  CodeBlockCode,
} from "@/features/chat/components/code-block";

export type MarkdownProps = {
  children: string;
  id?: string;
  className?: string;
  components?: Partial<Components>;
};

function extractLanguage(className?: string): string {
  if (!className) return "plaintext";
  const match = className.match(/language-(\w+)/);
  return match ? match[1] : "plaintext";
}

const INITIAL_COMPONENTS: Partial<Components> = {
  strong: function StrongComponent({ className, children, ...props }) {
    return (
      <strong className={cn("font-semibold", className)} {...props}>
        {children}
      </strong>
    );
  },
  code: function CodeComponent({ className, children, ...props }) {
    const isInline =
      !props.node?.position?.start.line ||
      props.node?.position?.start.line === props.node?.position?.end.line;

    if (isInline) {
      return (
        <span
          className={cn(
            "bg-primary-foreground rounded-sm px-1 font-mono text-sm",
            className,
          )}
          {...props}
        >
          {children}
        </span>
      );
    }

    const language = extractLanguage(className);

    return (
      <CodeBlock className={className}>
        <CodeBlockCode code={children as string} language={language} />
      </CodeBlock>
    );
  },
  pre: function PreComponent({ children }) {
    return <>{children}</>;
  },
};

function MarkdownComponent({
  children,
  id,
  className,
  components = INITIAL_COMPONENTS,
}: MarkdownProps) {
  return (
    <div className={className} id={id}>
      <Streamdown components={components} remarkPlugins={[remarkBreaks]}>
        {children}
      </Streamdown>
    </div>
  );
}

const Markdown = memo(MarkdownComponent);
Markdown.displayName = "Markdown";

export { Markdown };
