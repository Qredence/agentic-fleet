/**
 * Reasoning component - Re-exports from prompt-kit
 *
 * This module re-exports the prompt-kit Reasoning component for backwards
 * compatibility with existing imports from "@/components/message/reasoning".
 *
 * The prompt-kit version provides:
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
