import React from "react";
import { AgentGroup } from "./AgentGroup";
import { OrchestratorPanel } from "./OrchestratorPanel";
import { groupStepsByAgent, getOrchestratorSteps } from "./utils";
import type { WorkflowRendererProps } from "./types";

export const WorkflowRenderer: React.FC<WorkflowRendererProps> = ({
  steps,
  workflowPhase,
}) => {
  if (!steps || steps.length === 0) return null;

  const groups = groupStepsByAgent(steps);

  // Separate orchestrator from other agents
  const orchestratorSteps = groups.orchestrator?.steps || [];
  const agentEntries = Object.entries(groups).filter(
    ([id]) => id !== "orchestrator",
  );

  // Determine if orchestrator is active
  const isOrchestratorActive = Boolean(
    workflowPhase?.toLowerCase().includes("orchestrat") ||
      workflowPhase?.toLowerCase().includes("analyz") ||
      workflowPhase?.toLowerCase().includes("routing"),
  );

  return (
    <div className="space-y-3">
      {/* Orchestrator panel first (if has steps) */}
      {orchestratorSteps.length > 0 && (
        <OrchestratorPanel
          steps={getOrchestratorSteps(orchestratorSteps)}
          isActive={isOrchestratorActive}
        />
      )}

      {/* Agent groups */}
      {agentEntries.map(([agentId, data]) => (
        <AgentGroup
          key={agentId}
          agentId={agentId}
          name={data.name}
          avatar={data.avatar}
          steps={data.steps}
          isThinking={data.isThinking ?? false}
        />
      ))}
    </div>
  );
};

export default WorkflowRenderer;
