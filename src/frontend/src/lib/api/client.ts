import { API_BASE_URL } from "@/lib/config";

export interface WorkflowRequest {
  task: string;
  config?: Record<string, unknown>;
}

export interface WorkflowResponse {
  result: string;
  quality_score: number;
  execution_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface HistoryResponse {
  runs: Array<{
    run_id: string;
    status: string;
    task: string;
    result: string;
    routing?: Record<string, unknown>;
    agents?: string[];
    timing?: {
      total: number;
      phases: Record<string, number>;
    };
  }>;
}

export interface LogResponse {
  logs: Array<{
    timestamp: string;
    level: string;
    logger: string;
    message: string;
  }>;
}

export class AgenticFleetClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    return response.json();
  }

  async runWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await fetch(`${this.baseUrl}/workflows/run`, {
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

  async getHistory(limit: number = 20): Promise<HistoryResponse> {
    const response = await fetch(`${this.baseUrl}/history?last_n=${limit}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch history: ${response.statusText}`);
    }
    return response.json();
  }

  async getLogs(limit: number = 100): Promise<LogResponse> {
    const response = await fetch(`${this.baseUrl}/logs?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch logs: ${response.statusText}`);
    }
    return response.json();
  }
}

export const apiClient = new AgenticFleetClient();
