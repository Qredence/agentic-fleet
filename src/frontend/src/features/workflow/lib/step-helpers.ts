/**
 * Step creation and management utilities.
 *
 * Provides factory functions for creating conversation steps
 * with consistent structure and ID generation.
 */

import type { ConversationStep } from "@/api/types";

export function generateStepId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    // Use a UUID when available for strong uniqueness guarantees
    return `step-${crypto.randomUUID()}`;
  }

  // Fallback for environments without crypto.randomUUID
  return `step-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export function isDuplicateStep(
  existingSteps: ConversationStep[],
  newStep: ConversationStep,
): boolean {
  return existingSteps.some(
    (s) =>
      s.content === newStep.content &&
      s.type === newStep.type &&
      s.kind === newStep.kind &&
      (newStep.kind !== "request" ||
        s.data?.request_id === newStep.data?.request_id),
  );
}

/**
 * Factory function to create error steps with consistent structure.
 */
export function createErrorStep(
  content: string,
  data?: Record<string, unknown>,
): ConversationStep {
  return {
    id: generateStepId(),
    type: "error",
    content,
    timestamp: new Date().toISOString(),
    data,
  };
}

/**
 * Factory function to create status steps with consistent structure.
 */
export function createStatusStep(
  content: string,
  kind?: string,
  data?: Record<string, unknown>,
  options?: {
    category?: ConversationStep["category"];
    uiHint?: ConversationStep["uiHint"];
  },
): ConversationStep {
  return {
    id: generateStepId(),
    type: "status",
    content,
    timestamp: new Date().toISOString(),
    kind,
    data,
    category: options?.category,
    uiHint: options?.uiHint,
  };
}

/**
 * Factory function to create progress steps with consistent structure.
 */
export function createProgressStep(
  content: string,
  kind: string,
  data?: Record<string, unknown>,
): ConversationStep {
  return {
    id: generateStepId(),
    type: "progress",
    content,
    timestamp: new Date().toISOString(),
    kind,
    data,
  };
}
