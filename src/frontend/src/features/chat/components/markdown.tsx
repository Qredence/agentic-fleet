import { cn } from "@/lib/utils";
import { memo, type ComponentPropsWithoutRef } from "react";
import { Streamdown } from "streamdown";
import type { StreamdownProps } from "streamdown";
import { CodeBlock, CodeBlockCode } from "./code-block";

type Components = NonNullable<StreamdownProps["components"]>;

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
  strong: function StrongComponent({
    className,
    children,
    ...props
  }: ComponentPropsWithoutRef<"strong"> & { node?: any }) {
    return (
      <strong className={cn("font-semibold", className)} {...props}>
        {children}
      </strong>
    );
  },
  code: function CodeComponent({
    className,
    children,
    ...props
  }: ComponentPropsWithoutRef<"code"> & { node?: any }) {
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

    // For plaintext or empty language, render as simple preformatted text
    if (!language || language === "plaintext") {
      return (
        <pre
          className={cn(
            "overflow-x-auto rounded-md bg-muted/20 p-4 text-sm",
            className,
          )}
        >
          <code className="font-mono whitespace-pre">{children}</code>
        </pre>
      );
    }

    // For code blocks with a specified language, use CodeBlock component
    return (
      <CodeBlock className={className}>
        <CodeBlockCode
          code={
            Array.isArray(children) ? children.join("") : String(children ?? "")
          }
          language={language}
        />
      </CodeBlock>
    );
  },
  pre: function PreComponent({
    children,
  }: ComponentPropsWithoutRef<"pre"> & { node?: any }) {
    return <>{children}</>;
  },
};

function MarkdownComponent({
  children,
  className,
  components = INITIAL_COMPONENTS,
}: MarkdownProps) {
  return (
    <Streamdown className={className} components={components}>
      {children}
    </Streamdown>
  );
}

const Markdown = memo(MarkdownComponent);
Markdown.displayName = "Markdown";

export { Markdown };
