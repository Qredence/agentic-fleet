import { describe, expect, it, vi, beforeEach } from "vitest";

const httpMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/api/http", () => ({ http: httpMock }));

import { evaluationApi, improvementApi, optimizationApi } from "@/api/client";

beforeEach(() => {
  httpMock.get.mockReset();
  httpMock.post.mockReset();
});

describe("api client: optimization/evaluation/improvement", () => {
  it("optimizationApi.run posts to /optimization/jobs", async () => {
    httpMock.post.mockResolvedValueOnce({
      job_id: "job-123",
      status: "pending",
    });

    await optimizationApi.run({
      module_name: "DSPyReasoner",
      user_id: "user-1",
      auto_mode: "light",
    });

    expect(httpMock.post).toHaveBeenCalledWith("/optimization/jobs", {
      module_name: "DSPyReasoner",
      user_id: "user-1",
      auto_mode: "light",
    });
  });

  it("optimizationApi.status gets /optimization/jobs/{jobId}", async () => {
    httpMock.get.mockResolvedValueOnce({
      job_id: "job-123",
      status: "running",
    });

    await optimizationApi.status("job-123");

    expect(httpMock.get).toHaveBeenCalledWith("/optimization/jobs/job-123");
  });

  it("evaluationApi.history gets /history with limit/offset", async () => {
    httpMock.get.mockResolvedValueOnce([]);

    await evaluationApi.history({ limit: 10, offset: 20 });

    expect(httpMock.get).toHaveBeenCalledWith("/history?limit=10&offset=20");
  });

  it("improvementApi.trigger throws error (deprecated)", async () => {
    await expect(improvementApi.trigger({})).rejects.toThrow(
      "Use optimizationApi.run instead",
    );
  });
});
