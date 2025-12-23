// Workflow UI components
export { ChainOfThoughtTrace } from "./chain-of-thought";
export { WorkflowRequestResponder } from "./workflow-request-responder";

// Step variants for dynamic component rendering
export {
  ChatStepVariant,
  MessageBubbleVariant,
  InlineTextVariant,
} from "./step-variants";
export type { StepVariantProps } from "./step-variants";

// Component registry for backend-driven UI selection
export {
  COMPONENT_REGISTRY,
  resolveComponent,
  shouldBeCollapsible,
  isRegisteredComponent,
  getRegisteredComponents,
} from "./component-registry";
