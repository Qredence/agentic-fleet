import type { ConversationStep } from "../../api/types";
import type { AgentGroups } from "./types";

const ORCHESTRATOR_KINDS = ["routing", "analysis", "quality", "progress"];

export function getAgentDisplayName(agentId: string): string {
  if (agentId === "orchestrator") return "Orchestrator";

  // Clean up agent IDs like "PlannerAgent" -> "Planner"
  const cleaned = agentId
    .replace(/Agent$/i, "")
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2");

  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function getAgentAvatar(agentId: string): string | undefined {
  // Could be extended to return actual avatar URLs based on agentId
  // Map known agents to avatar URLs if needed
  const avatarMap: Record<string, string> = {
    // Add avatar mappings here when available
    // "planner": "/avatars/planner.png",
  };
  return avatarMap[agentId.toLowerCase()];
}

export function groupStepsByAgent(steps: ConversationStep[]): AgentGroups {
  const groups: AgentGroups = {};

  for (const step of steps) {
    // Determine agent from step data or kind
    let agentId: string;

    // Orchestrator events: routing, analysis, quality, progress
    if (ORCHESTRATOR_KINDS.includes(step.kind || "")) {
      agentId = "orchestrator";
    } else if (step.type === "thought" || step.type === "status") {
      // Generic thought/status events go to orchestrator
      agentId = "orchestrator";
    } else {
      // Agent-specific events
      const data = step.data as Record<string, unknown> | undefined;
      agentId =
        (data?.agent_id as string) ||
        (data?.author as string) ||
        "orchestrator";
    }

    if (!groups[agentId]) {
      groups[agentId] = {
        name: getAgentDisplayName(agentId),
        avatar: getAgentAvatar(agentId),
        steps: [],
        isThinking: false,
      };
    }

    groups[agentId].steps.push(step);

    // Track thinking state
    if (step.type === "agent_start") {
      groups[agentId].isThinking = true;
    }
    if (step.type === "agent_complete" || step.type === "agent_output") {
      groups[agentId].isThinking = false;
    }
  }

  return groups;
}

export function hasReasoningSteps(steps: ConversationStep[]): boolean {
  return steps.some((s) => s.type === "reasoning");
}

export function hasThoughtSteps(steps: ConversationStep[]): boolean {
  return steps.some(
    (s) =>
      s.type === "thought" ||
      s.type === "agent_thought" ||
      s.type === "routing" ||
      s.type === "analysis" ||
      s.type === "quality",
  );
}

export function hasOutputSteps(steps: ConversationStep[]): boolean {
  return steps.some((s) => s.type === "agent_output");
}

export function getReasoningContent(steps: ConversationStep[]): string {
  return steps
    .filter((s) => s.type === "reasoning")
    .map((s) => s.content)
    .join("\n\n");
}

export function getOutputContent(steps: ConversationStep[]): string {
  return steps
    .filter((s) => s.type === "agent_output")
    .map((s) => {
      // Prefer output from data field (actual content), fall back to step content
      const data = s.data as Record<string, unknown> | undefined;
      return (data?.output as string) || s.content;
    })
    .join("\n\n");
}

export function getThoughtSteps(steps: ConversationStep[]): ConversationStep[] {
  return steps.filter(
    (s) =>
      s.type === "thought" ||
      s.type === "agent_thought" ||
      s.type === "routing" ||
      s.type === "analysis" ||
      s.type === "quality" ||
      s.type === "handoff" ||
      s.type === "tool_call",
  );
}

export function getOrchestratorSteps(
  steps: ConversationStep[],
): ConversationStep[] {
  return steps.filter(
    (s) =>
      s.kind === "routing" ||
      s.kind === "analysis" ||
      s.kind === "quality" ||
      s.kind === "progress" ||
      s.type === "thought" ||
      s.type === "status",
  );
}

// Generic status messages that don't add value to the UI
const GENERIC_STATUS_PATTERNS = [
  /^Starting workflow execution/i,
  /^Workflow started$/i,
  /^Workflow status: (IN_PROGRESS|IDLE|RUNNING|COMPLETED)$/i,
  /^Status update$/i,
  /^Processing\.\.\.$/i,
];

/**
 * Filter out generic status messages that don't provide useful information.
 * Keeps: analysis, routing, quality, agent events, actual content
 * Removes: generic "Workflow started", "Status: IN_PROGRESS", etc.
 */
export function filterUsefulSteps(
  steps: ConversationStep[],
): ConversationStep[] {
  return steps.filter((step) => {
    // Always keep steps with meaningful kind (analysis, routing, quality, progress)
    if (step.kind && ORCHESTRATOR_KINDS.includes(step.kind)) {
      return true;
    }

    // Always keep agent events
    if (
      step.type === "agent_start" ||
      step.type === "agent_complete" ||
      step.type === "agent_output" ||
      step.type === "agent_thought"
    ) {
      return true;
    }

    // Always keep reasoning events
    if (step.type === "reasoning") {
      return true;
    }

    // Filter out generic status messages
    const content = step.content || "";
    const isGeneric = GENERIC_STATUS_PATTERNS.some((pattern) =>
      pattern.test(content),
    );

    if (isGeneric) {
      return false;
    }

    // Keep anything with actual data
    if (step.data && Object.keys(step.data).length > 0) {
      return true;
    }

    // Keep thought events with content
    if (step.type === "thought" && content.length > 20) {
      return true;
    }

    // Filter out very short generic status messages
    if (step.type === "status" && content.length < 50) {
      // Check if it's actually meaningful
      const hasKeywords =
        /analysis|routing|quality|agent|tool|error|complete/i.test(content);
      return hasKeywords;
    }

    return true;
  });
}

/**
 * Get a summary of filtered-out steps for display.
 */
export function getFilteredSummary(
  originalSteps: ConversationStep[],
  filteredSteps: ConversationStep[],
): string | null {
  const removed = originalSteps.length - filteredSteps.length;
  if (removed > 0) {
    return `${removed} status update${removed > 1 ? "s" : ""} hidden`;
  }
  return null;
}
