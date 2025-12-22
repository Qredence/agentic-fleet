/**
 * Shared constants for the frontend application
 */

export const DEFAULT_CONVERSATION_TITLE = "New Chat";

export type ExecutionMode = "auto" | "fast" | "standard";

export const EXECUTION_MODES: readonly ExecutionMode[] = [
  "auto",
  "fast",
  "standard",
] as const;
