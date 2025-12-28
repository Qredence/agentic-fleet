import type { ConversationStep } from "@/api/types";
import type { StepVariantProps } from "./step-variants";
import {
  ChatStepVariant,
  MessageBubbleVariant,
  InlineTextVariant,
} from "./step-variants";

/**
 * Component registry mapping component names to React component implementations.
 * This enables backend-driven UI component selection via ui_hint.component.
 */
export const COMPONENT_REGISTRY: Record<
  string,
  React.ComponentType<StepVariantProps>
> = {
  ChatStep: ChatStepVariant,
  MessageBubble: MessageBubbleVariant,
  InlineText: InlineTextVariant,
};

/**
 * Default component when no hint is provided or component name is unknown.
 */
const DEFAULT_COMPONENT = ChatStepVariant;

/**
 * Resolves which component variant to use for rendering a step.
 *
 * Resolution order:
 * 1. Check step.uiHint.component and lookup in registry
 * 2. Fall back to type-based heuristics
 * 3. Use default component (ChatStepVariant)
 *
 * @param step - The conversation step to resolve a component for
 * @returns React component for rendering the step
 */
export function resolveComponent(
  step: ConversationStep,
): React.ComponentType<StepVariantProps> {
  // Priority 1: Special-case low-priority status/progress to InlineText
  // even if uiHint.component is provided by backend for backward compatibility.
  if (
    (step.type === "status" || step.type === "progress") &&
    step.uiHint?.priority === "low"
  ) {
    return InlineTextVariant;
  }

  // Priority 2: Use ui_hint.component if provided and registered
  const componentName = step.uiHint?.component;
  if (componentName && COMPONENT_REGISTRY[componentName]) {
    return COMPONENT_REGISTRY[componentName];
  }

  // Priority 2: Type-based heuristics for backward compatibility
  // Response-related events should use MessageBubble
  if (step.category === "response" || step.type === "agent_output") {
    return MessageBubbleVariant;
  }

  // Priority 3: Default to ChatStep for all other cases
  return DEFAULT_COMPONENT;
}

/**
 * Determines whether a step should be collapsible based on its properties.
 *
 * Resolution order:
 * 1. Check step.uiHint.collapsible if provided
 * 2. Fall back to type-based rules
 * 3. Default to collapsible(true)
 *
 * @param step - The conversation step to check
 * @returns true if the step should be collapsible, false for always-expanded
 */
export function shouldBeCollapsible(step: ConversationStep): boolean {
  // Priority 1: Respect backend hint if provided
  if (step.uiHint && typeof step.uiHint.collapsible === "boolean") {
    return step.uiHint.collapsible;
  }

  // Priority 2: Type-based heuristics for backward compatibility
  // Response and output events are typically not collapsible
  if (
    step.category === "response" ||
    step.type === "agent_output" ||
    step.uiHint?.component === "MessageBubble"
  ) {
    return false;
  }

  // Reasoning steps are typically collapsible
  if (step.type === "reasoning" || step.category === "reasoning") {
    return true;
  }

  // Priority 3: Default to collapsible
  return true;
}

/**
 * Type guard to check if a component name is registered.
 *
 * @param componentName - Component name to check
 * @returns true if component is in registry
 */
export function isRegisteredComponent(componentName: string): boolean {
  return componentName in COMPONENT_REGISTRY;
}

/**
 * Gets all registered component names.
 *
 * @returns Array of registered component names
 */
export function getRegisteredComponents(): string[] {
  return Object.keys(COMPONENT_REGISTRY);
}
