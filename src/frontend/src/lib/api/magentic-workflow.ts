/**
 * Magentic Workflow API Client
 *
 * Provides TypeScript client for interacting with Magentic workflows
 * via SSE streaming and REST endpoints.
 */

import { API_BASE_URL } from "../config";

/**
 * Magentic workflow event from SSE stream
 */
export interface MagenticWorkflowEvent {
  type: string;
  data?: Record<string, unknown>;
}

/**
 * Workflow status response
 */
export interface WorkflowStatus {
  workflow_id: string;
  task: string;
  status: "created" | "running" | "completed" | "failed" | "paused";
  round_count: number;
  phase: "plan" | "evaluate" | "act" | "observe" | "complete";
  stall_count: number;
  reset_count: number;
  max_rounds: number;
  observations_count: number;
}

/**
 * Workflow creation request
 */
export interface CreateWorkflowRequest {
  task: string;
  config?: {
    max_rounds?: number;
    max_stalls?: number;
    max_resets?: number;
  };
}

/**
 * Workflow creation response
 */
export interface CreateWorkflowResponse {
  workflow_id: string;
  task: string;
  status: string;
}

/**
 * Client for Magentic workflow API interactions.
 *
 * Provides methods for:
 * - Creating workflows
 * - Streaming workflow execution via SSE
 * - Checking workflow status
 * - Managing workflow lifecycle (pause/resume/delete)
 *
 * @example
 * ```typescript
 * const client = new MagenticWorkflowClient();
 *
 * // Create workflow
 * const { workflow_id } = await client.createWorkflow({
 *   task: "Research quantum computing"
 * });
 *
 * // Stream execution
 * const cleanup = client.streamWorkflow(
 *   workflow_id,
 *   (event) => console.log('Event:', event),
 *   (error) => console.error('Error:', error)
 * );
 *
 * // Cleanup when done
 * cleanup();
 * ```
 */
export class MagenticWorkflowClient {
  private eventSource: EventSource | null = null;
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Create a new workflow
   *
   * @param request - Workflow creation request with task and config
   * @returns Promise resolving to workflow creation response
   * @throws Error if creation fails
   */
  async createWorkflow(
    request: CreateWorkflowRequest,
  ): Promise<CreateWorkflowResponse> {
    const response = await fetch(`${this.baseUrl}/v1/workflows`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Failed to create workflow: ${response.statusText} - ${error}`,
      );
    }

    return response.json();
  }

  /**
   * Execute workflow with SSE streaming
   *
   * Opens an SSE connection to stream workflow events in real-time.
   * Events include workflow progress, agent actions, and completion.
   *
   * @param workflowId - Workflow ID to execute
   * @param onEvent - Callback for each event
   * @param onError - Optional error handler
   * @returns Cleanup function to close the SSE connection
   *
   * @example
   * ```typescript
   * const cleanup = client.streamWorkflow(
   *   workflowId,
   *   (event) => {
   *     switch (event.type) {
   *       case 'plan_created':
   *         console.log('Plan:', event.data.plan);
   *         break;
   *       case 'agent_start':
   *         console.log('Agent:', event.data.agent);
   *         break;
   *       case 'workflow_complete':
   *         console.log('Completed!');
   *         cleanup();
   *         break;
   *     }
   *   }
   * );
   * ```
   */
  streamWorkflow(
    workflowId: string,
    onEvent: (event: MagenticWorkflowEvent) => void,
    onError?: (error: Error) => void,
  ): () => void {
    // Close existing connection if any
    this.disconnect();

    // Create new SSE connection
    const url = `${this.baseUrl}/v1/workflows/${workflowId}/stream`;
    this.eventSource = new EventSource(url);

    // Handle messages
    this.eventSource.onmessage = (messageEvent) => {
      try {
        const event: MagenticWorkflowEvent = JSON.parse(messageEvent.data);
        onEvent(event);
      } catch (error) {
        console.error("Failed to parse SSE event:", error);
        onError?.(error as Error);
      }
    };

    // Handle errors
    this.eventSource.onerror = (error) => {
      console.error("SSE connection error:", error);
      onError?.(new Error("SSE connection error"));

      // Auto-reconnect behavior is handled by EventSource
      // but we'll disconnect on error
      this.disconnect();
    };

    // Return cleanup function
    return () => this.disconnect();
  }

  /**
   * Get workflow status
   *
   * @param workflowId - Workflow ID to query
   * @returns Promise resolving to workflow status
   * @throws Error if workflow not found or request fails
   */
  async getWorkflowStatus(workflowId: string): Promise<WorkflowStatus> {
    const response = await fetch(
      `${this.baseUrl}/v1/workflows/${workflowId}/status`,
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Failed to get workflow status: ${response.statusText} - ${error}`,
      );
    }

    return response.json();
  }

  /**
   * List all active workflows
   *
   * @returns Promise resolving to list of workflow statuses
   */
  async listWorkflows(): Promise<WorkflowStatus[]> {
    const response = await fetch(`${this.baseUrl}/v1/workflows`);

    if (!response.ok) {
      throw new Error(`Failed to list workflows: ${response.statusText}`);
    }

    const data = await response.json();
    return data.workflows || [];
  }

  /**
   * Delete a workflow
   *
   * Removes workflow from active sessions.
   *
   * @param workflowId - Workflow ID to delete
   * @returns Promise resolving when deletion completes
   * @throws Error if deletion fails
   */
  async deleteWorkflow(workflowId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/workflows/${workflowId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Failed to delete workflow: ${response.statusText} - ${error}`,
      );
    }
  }

  /**
   * Pause workflow execution
   *
   * Note: Requires checkpointing to be enabled.
   *
   * @param workflowId - Workflow ID to pause
   * @returns Promise resolving to updated workflow status
   * @throws Error if pause fails
   */
  async pauseWorkflow(workflowId: string): Promise<WorkflowStatus> {
    const response = await fetch(
      `${this.baseUrl}/v1/workflows/${workflowId}/pause`,
      {
        method: "POST",
      },
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Failed to pause workflow: ${response.statusText} - ${error}`,
      );
    }

    return response.json();
  }

  /**
   * Resume paused workflow with SSE streaming
   *
   * @param workflowId - Workflow ID to resume
   * @param onEvent - Callback for each event
   * @param onError - Optional error handler
   * @returns Cleanup function to close the SSE connection
   */
  resumeWorkflow(
    workflowId: string,
    onEvent: (event: MagenticWorkflowEvent) => void,
    onError?: (error: Error) => void,
  ): () => void {
    // Close existing connection
    this.disconnect();

    // Create SSE connection to resume endpoint
    const url = `${this.baseUrl}/v1/workflows/${workflowId}/resume`;
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (messageEvent) => {
      try {
        const event: MagenticWorkflowEvent = JSON.parse(messageEvent.data);
        onEvent(event);
      } catch (error) {
        console.error("Failed to parse SSE event:", error);
        onError?.(error as Error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error("SSE connection error:", error);
      onError?.(new Error("SSE connection error"));
      this.disconnect();
    };

    return () => this.disconnect();
  }

  /**
   * Disconnect active SSE connection
   *
   * Call this to manually close the event stream.
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Check if SSE connection is active
   */
  isConnected(): boolean {
    return (
      this.eventSource !== null &&
      this.eventSource.readyState === EventSource.OPEN
    );
  }
}

/**
 * Singleton instance for convenience
 */
export const workflowClient = new MagenticWorkflowClient();
