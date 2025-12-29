import React, { Component, type ReactNode } from "react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of crashing.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console in development
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    // Call optional error handler
    this.props.onError?.(error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error } = this.state;
      const isDev = import.meta.env.DEV;

      return (
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="w-full max-w-2xl">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription className="mt-2">
                <p className="mb-2">
                  An unexpected error occurred. Please try refreshing the page
                  or contact support if the problem persists.
                </p>
                {isDev && error && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm font-medium">
                      Error Details (Development Only)
                    </summary>
                    <pre className="mt-2 overflow-auto rounded bg-muted p-2 text-xs">
                      {error.toString()}
                      {this.state.errorInfo?.componentStack && (
                        <div className="mt-2 border-t pt-2">
                          <div className="font-semibold">Component Stack:</div>
                          <pre className="mt-1 whitespace-pre-wrap">
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </div>
                      )}
                    </pre>
                  </details>
                )}
              </AlertDescription>
            </Alert>
            <div className="mt-4 flex gap-2">
              <Button onClick={this.handleReset} variant="outline">
                Try Again
              </Button>
              <Button
                onClick={() => {
                  window.location.reload();
                }}
              >
                Reload Page
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
