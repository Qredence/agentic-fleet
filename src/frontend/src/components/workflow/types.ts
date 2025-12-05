import type { ConversationStep } from "../../api/types";

export interface AgentGroupData {
  name: string;
  avatar?: string;
  steps: ConversationStep[];
  isThinking: boolean;
}

export type AgentGroups = Record<string, AgentGroupData>;

export interface WorkflowRendererProps {
  steps: ConversationStep[];
  workflowPhase?: string;
}

export interface AgentGroupProps {
  agentId: string;
  name: string;
  avatar?: string;
  steps: ConversationStep[];
  isThinking: boolean;
}

export interface OrchestratorPanelProps {
  steps: ConversationStep[];
  isActive: boolean;
}
