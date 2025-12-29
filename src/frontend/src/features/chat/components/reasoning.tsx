/**
 * Reasoning component - Re-exports from UI primitives
 *
 * This module re-exports the UI Reasoning component for backwards
 * compatibility with existing imports from "./components/reasoning".
 *
 * The UI component provides:
 * - Auto-open on streaming, auto-close when done (isStreaming prop)
 * - Built-in markdown support
 * - Smooth height animations
 */
export {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
  type ReasoningProps,
  type ReasoningTriggerProps,
  type ReasoningContentProps,
} from "@/components/ui/reasoning";
