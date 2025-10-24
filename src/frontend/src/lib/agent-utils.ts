/**
 * Utility functions for mapping agent roles and actors to display types
 */

import type { AgentType } from "@/components/ChatMessage";

/**
 * Maps a role and optional actor to an AgentType for display purposes
 * 
 * @param role - The role of the message sender (e.g., "assistant", "user", "system")
 * @param actor - Optional actor name (e.g., "analyst", "researcher", "coder")
 * @returns The appropriate AgentType for rendering
 */
export function mapRoleToAgent(role: string, actor?: string): AgentType {
  // If the role is "user", always return "user"
  if (role === "user") {
    return "user";
  }

  // If an actor is specified, try to map it to a known agent type
  if (actor) {
    const lowerActor = actor.toLowerCase();
    
    // Direct mappings for known agent types
    if (lowerActor === "analyst" || lowerActor.includes("analyst")) {
      return "analyst";
    }
    if (lowerActor === "researcher" || lowerActor.includes("researcher")) {
      return "researcher";
    }
    if (lowerActor === "strategist" || lowerActor.includes("strateg")) {
      return "strategist";
    }
    if (lowerActor === "coordinator" || lowerActor === "orchestrator" || lowerActor.includes("coordinat")) {
      return "coordinator";
    }
    if (lowerActor === "worker" || lowerActor === "coder" || lowerActor.includes("worker")) {
      return "worker";
    }
  }

  // Default fallback - coordinator for assistant/system roles
  return "coordinator";
}
