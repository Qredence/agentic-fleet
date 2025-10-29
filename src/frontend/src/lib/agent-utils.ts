import type { AgentRole, MessageRole } from "./types";

const ROLE_ALIAS_MAP: Record<string, AgentRole> = {
  manager: "manager",
  orchestrator: "manager",
  planner: "planner",
  executor: "executor",
  coder: "coder",
  engineer: "coder",
  verifier: "verifier",
  reviewer: "verifier",
  generator: "generator",
  analyst: "analyst",
  researcher: "researcher",
};

export function mapRoleToAgent(
  role: MessageRole,
  agentRole?: string | null,
): AgentRole {
  if (role === "user") {
    return "user";
  }

  if (agentRole) {
    const alias = ROLE_ALIAS_MAP[agentRole.toLowerCase()];
    if (alias) {
      return alias;
    }
  }

  if (role === "assistant") {
    return "assistant";
  }

  const fallback = ROLE_ALIAS_MAP[role.toLowerCase()];
  return fallback ?? "assistant";
}
