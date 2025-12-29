import { z } from "zod";

// =============================================================================
// Common Schemas
// =============================================================================

export const ConversationStepDataSchema = z.record(z.string(), z.unknown()).and(
  z.object({
    request_id: z.string().optional(),
    agent_id: z.string().optional(),
    author: z.string().optional(),
    output: z.string().optional(),
    phase: z.string().optional(),
  }),
);

export const UIHintSchema = z.object({
  component: z.string(),
  priority: z.enum(["low", "medium", "high"]),
  collapsible: z.boolean(),
  iconHint: z.string().optional(),
});

export const StepCategorySchema = z.enum([
  "step",
  "thought",
  "reasoning",
  "planning",
  "output",
  "response",
  "status",
  "error",
]);

export const ConversationStepSchema = z.object({
  id: z.string(),
  type: z.enum([
    "thought",
    "status",
    "request",
    "reasoning",
    "error",
    "agent_start",
    "agent_complete",
    "agent_output",
    "agent_thought",
    "agent_message",
    "routing",
    "analysis",
    "quality",
    "handoff",
    "tool_call",
    "progress",
  ]),
  content: z.string(),
  timestamp: z.string(),
  kind: z.string().optional(),
  data: ConversationStepDataSchema.optional(),
  isExpanded: z.boolean().optional(),
  category: StepCategorySchema.optional(),
  uiHint: UIHintSchema.optional(),
});

export const MessageSchema = z.object({
  id: z.string().optional(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  created_at: z.string(),
  agent_id: z.string().optional(),
  author: z.string().optional(),
  steps: z.array(ConversationStepSchema).optional(),
  groupId: z.string().optional(),
  isWorkflowPlaceholder: z.boolean().optional(),
  workflowPhase: z.string().optional(),
  qualityFlag: z.string().optional(),
  qualityScore: z.number().optional(),
  narrative: z.string().optional(),
  isFast: z.boolean().optional(),
  latency: z.string().optional(),
  completedPhases: z.array(z.string()).optional(),
});

export const ConversationSchema = z.object({
  conversation_id: z.string(),
  title: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  messages: z.array(MessageSchema),
});

// =============================================================================
// Request Schemas
// =============================================================================

export const ReasoningEffortSchema = z.enum(["minimal", "medium", "maximal"]);

export const ChatRequestSchema = z.object({
  conversation_id: z.string(),
  message: z.string(),
  stream: z.boolean().optional(),
  reasoning_effort: ReasoningEffortSchema.optional(),
  enable_checkpointing: z.boolean().optional(),
  checkpoint_id: z.string().optional(),
});

export const WorkflowResumeRequestSchema = z.object({
  type: z.literal("workflow.resume"),
  conversation_id: z.string().optional(),
  checkpoint_id: z.string(),
  stream: z.boolean().optional(),
  reasoning_effort: ReasoningEffortSchema.optional(),
});

export const CancelRequestSchema = z.object({
  type: z.literal("cancel"),
});

export const WorkflowResponseRequestSchema = z.object({
  type: z.literal("workflow.response"),
  request_id: z.string(),
  response: z.unknown(),
});

export const CreateConversationRequestSchema = z.object({
  title: z.string().optional(),
});

// =============================================================================
// Event Schemas
// =============================================================================

export const StreamEventSchema = z.object({
  type: z.enum([
    "response.delta",
    "response.completed",
    "error",
    "orchestrator.message",
    "orchestrator.thought",
    "reasoning.delta",
    "reasoning.completed",
    "done",
    "agent.start",
    "agent.complete",
    "agent.output",
    "agent.thought",
    "agent.message",
    "connected",
    "cancelled",
    "heartbeat",
    "workflow.status",
  ]),
  delta: z.string().optional(),
  agent_id: z.string().optional(),
  author: z.string().optional(),
  role: z.enum(["user", "assistant", "system"]).optional(),
  content: z.string().optional(),
  message: z.string().optional(),
  error: z.string().optional(),
  reasoning: z.string().optional(),
  kind: z.string().optional(),
  data: ConversationStepDataSchema.optional(),
  timestamp: z.string().optional(),
  reasoning_partial: z.boolean().optional(),
  quality_score: z.number().optional(),
  quality_flag: z.string().optional(),
  category: z.string().optional(),
  ui_hint: z
    .object({
      component: z.string(),
      priority: z.enum(["low", "medium", "high"]),
      collapsible: z.boolean(),
      icon_hint: z.string().optional(),
    })
    .optional(),
  workflow_id: z.string().optional(),
  log_line: z.string().optional(),
  status: z.enum(["in_progress", "failed", "idle", "completed"]).optional(),
});

// =============================================================================
// Other Schemas
// =============================================================================

export const WorkflowSessionSchema = z.object({
  workflow_id: z.string(),
  task: z.string(),
  status: z.enum(["created", "running", "completed", "failed", "cancelled"]),
  created_at: z.string(),
  started_at: z.string().optional(),
  completed_at: z.string().optional(),
  reasoning_effort: z.string().optional(),
});

export const AgentInfoSchema = z.object({
  name: z.string(),
  description: z.string(),
  type: z.string(),
});

export const IntentRequestSchema = z.object({
  text: z.string(),
  possible_intents: z.array(z.string()),
});

export const IntentResponseSchema = z.object({
  intent: z.string(),
  confidence: z.number(),
  reasoning: z.string(),
});

export const EntityRequestSchema = z.object({
  text: z.string(),
  entity_types: z.array(z.string()),
});

export const EntityResponseSchema = z.object({
  entities: z.array(
    z.object({
      text: z.string(),
      type: z.string(),
      confidence: z.string(),
    }),
  ),
  reasoning: z.string(),
});
