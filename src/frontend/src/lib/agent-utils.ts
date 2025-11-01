/**
 * Agent Utility Functions
 *
 * Maps backend agent/role information to frontend AgentType for UI rendering
 */

import type { AgentType } from "./types";

/**
 * Map a message role and optional actor name to an AgentType for UI rendering
 *
 * @param role - The message role (user, assistant, system)
 * @param actor - Optional actor name from the backend (e.g., "Researcher Agent", "Coder Agent")
 * @returns AgentType for UI rendering
 */
export function mapRoleToAgent(role: string, actor?: string): AgentType {
  // User messages are always mapped to user
  if (role === "user") {
    return "user";
  }

  // If we have an actor, try to map it to a specific agent type
  if (actor) {
    const actorLower = actor.toLowerCase();

    // Research-related agents
    if (actorLower.includes("research") || actorLower.includes("web")) {
      return "researcher";
    }

    // Analysis/data-related agents
    if (
      actorLower.includes("analyst") ||
      actorLower.includes("analysis") ||
      actorLower.includes("data")
    ) {
      return "analyst";
    }

    // Strategy/planning-related agents
    if (
      actorLower.includes("strateg") ||
      actorLower.includes("plan") ||
      actorLower.includes("orchestrat") ||
      actorLower.includes("manager")
    ) {
      return "strategist";
    }

    // Coordinator/system agents
    if (
      actorLower.includes("coordinat") ||
      actorLower.includes("system") ||
      actorLower.includes("fleet")
    ) {
      return "coordinator";
    }
  }

  // Default mapping based on role
  if (role === "system") {
    return "coordinator";
  }

  // Default to coordinator for assistant messages without specific actor
  return "coordinator";
}
