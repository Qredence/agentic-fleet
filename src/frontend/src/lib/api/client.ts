import { API_BASE_URL } from "@/lib/config";

export interface WorkflowRequest {
  task: string;
  config?: Record<string, any>;
}

export interface WorkflowResponse {
  result: string;
  quality_score: number;
  execution_summary: Record<string, any>;
  metadata: Record<string, any>;
}

export class AgenticFleetClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async runWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await fetch(`${this.baseUrl}/workflow/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Workflow failed: ${response.status} ${response.statusText} - ${errorText}`,
      );
    }

    return response.json();
  }
}

export const apiClient = new AgenticFleetClient();
