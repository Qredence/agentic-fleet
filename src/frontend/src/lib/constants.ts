// Shared constants for the frontend application

// Types of steps that should be displayed as workflow events
export const WORKFLOW_EVENT_TYPES = [
  "status",
  "agent_start",
  "agent_complete",
  "thought",
  "agent_thought",
  "agent_output",
  "routing", // NEW: routing decisions
  "analysis", // NEW: task analysis
  "quality", // NEW: quality assessment
  "handoff", // NEW: agent handoffs
  "tool_call", // NEW: tool invocations
  "progress", // NEW: progress updates
] as const;

export type WorkflowEventType = (typeof WORKFLOW_EVENT_TYPES)[number];

// Types of steps that should be displayed as chain-of-thought reasoning
export const REASONING_STEP_TYPES = ["reasoning"] as const;

export type ReasoningStepType = (typeof REASONING_STEP_TYPES)[number];

// Reasoning effort levels for GPT-5 models
export type ReasoningEffort = "minimal" | "medium" | "maximal";

// Workflow modes
export const WORKFLOW_MODES = [
  "auto",
  "standard",
  "group_chat",
  "concurrent",
  "handoff",
] as const;

export type WorkflowMode = (typeof WORKFLOW_MODES)[number];
