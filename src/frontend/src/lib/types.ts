/**
 * Shared type definitions for the application
 */

/**
 * Tool call information from backend
 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  status?: "running" | "complete" | "error";
}

/**
 * Message structure from the chat system
 */
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  actor?: string;
  isNew?: boolean;
  isStreaming?: boolean;
  tool_calls?: ToolCall[];
}

/**
 * Agent type for UI rendering
 */
export type AgentType =
  | "user"
  | "analyst"
  | "researcher"
  | "strategist"
  | "coordinator";
