import * as React from "react";
import { Code } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/ui/code-block";

export interface JsxPreviewProps {
  jsx: string;
  className?: string;
  showCode?: boolean;
  fallback?: React.ReactNode;
}

const DEFAULT_FALLBACK = (
  <div className="text-sm text-muted-foreground">No JSX snippet provided.</div>
);

const JsxPreview = React.forwardRef<HTMLDivElement, JsxPreviewProps>(
  (
    { jsx, className, showCode = false, fallback = DEFAULT_FALLBACK, ...props },
    ref,
  ) => {
    const [showSource, setShowSource] = React.useState(showCode);
    const trimmedJsx = React.useMemo(() => jsx.trim(), [jsx]);
    const hasContent = trimmedJsx.length > 0;

    if (!hasContent) {
      return (
        <div
          ref={ref}
          className={cn(
            "border rounded-lg bg-muted/10 p-4 text-muted-foreground",
            className,
          )}
          {...props}
        >
          {fallback}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn("border rounded-lg overflow-hidden", className)}
        {...props}
      >
        <div className="flex items-center justify-between border-b bg-muted/20 px-3 py-2">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Code className="size-4" />
            <span>JSX Preview</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => setShowSource((prev) => !prev)}
          >
            {showSource ? "Hide" : "Show"} Code
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {!showSource && (
            <div className="flex min-h-[100px] items-center justify-center rounded border-2 border-dashed border-muted-foreground/20 bg-muted/10 text-center text-sm text-muted-foreground">
              Toggle &ldquo;Show Code&rdquo; to view the JSX snippet.
            </div>
          )}
          {showSource && (
            <CodeBlock className="max-h-96 overflow-auto text-sm">
              <pre>
                <code>{trimmedJsx}</code>
              </pre>
            </CodeBlock>
          )}
        </div>
      </div>
    );
  },
);

JsxPreview.displayName = "JsxPreview";

export { JsxPreview };
