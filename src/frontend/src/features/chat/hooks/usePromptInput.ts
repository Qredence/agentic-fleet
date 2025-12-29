import * as React from "react";

// =============================================================================
// Types
// =============================================================================

export interface PromptInputContextValue {
  isLoading?: boolean;
  value: string;
  setValue: (value: string) => void;
  maxHeight?: number | string;
  onSubmit?: () => void;
  disabled?: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}

// =============================================================================
// Context
// =============================================================================

export const PromptInputContext =
  React.createContext<PromptInputContextValue | null>(null);

// =============================================================================
// Hook
// =============================================================================

export function usePromptInput(): PromptInputContextValue {
  const context = React.useContext(PromptInputContext);
  if (!context) {
    throw new Error(
      "usePromptInput must be used within a PromptInput component",
    );
  }
  return context;
}
