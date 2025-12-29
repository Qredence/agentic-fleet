/**
 * Workflow phase detection utilities.
 *
 * Maps stream events to user-friendly workflow phase descriptions.
 */

import type { StreamEvent } from "@/api/types";

export function getWorkflowPhase(event: StreamEvent): string {
  if (event.type === "connected") return "Connected";
  if (event.type === "cancelled") return "Cancelled";
  if (event.type === "workflow.status") {
    if (event.status === "failed") return "Failed";
    if (event.status === "in_progress") return "Starting...";
    return "Processing...";
  }
  if (event.kind === "request") return "Awaiting input...";
  if (event.kind === "routing") return "Routing...";
  if (event.kind === "analysis") return "Analyzing...";
  if (event.kind === "quality") return "Quality check...";
  if (event.kind === "progress") return "Processing...";
  if (event.type === "agent.start")
    return `Starting ${event.author || event.agent_id || "agent"}...`;
  if (event.type === "agent.complete") return "Completing...";
  if (event.type === "agent.message") return "Agent replying...";
  if (event.type === "agent.output") return "Agent outputting...";
  if (event.type === "reasoning.delta") return "Reasoning...";
  return "Processing...";
}
