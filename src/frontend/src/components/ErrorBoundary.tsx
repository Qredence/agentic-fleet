/**
 * Error Boundary component for catching React errors
 * Displays user-friendly error UI instead of white screen
 */

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";
import React, { ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error info to console in development
    if (import.meta.env.DEV) {
      console.error("Error caught by boundary:", error, errorInfo);
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex items-center justify-center min-h-screen bg-background p-4">
            <div className="w-full max-w-md">
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Something went wrong</AlertTitle>
                <AlertDescription className="mt-2">
                  <p className="text-sm">An unexpected error occurred. Please refresh the page.</p>
                  {import.meta.env.DEV && this.state.error && (
                    <details className="mt-4 p-2 bg-destructive/10 rounded text-xs font-mono">
                      <summary className="cursor-pointer font-semibold">Error details</summary>
                      <pre className="mt-2 whitespace-pre-wrap break-words">
                        {this.state.error.toString()}
                      </pre>
                    </details>
                  )}
                </AlertDescription>
              </Alert>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
