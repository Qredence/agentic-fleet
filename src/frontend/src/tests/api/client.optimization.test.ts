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
  it("optimizationApi.run posts to /optimize", async () => {
    httpMock.post.mockResolvedValueOnce({ status: "started", message: "ok" });

    await optimizationApi.run({ optimizer: "gepa", use_cache: true });

    expect(httpMock.post).toHaveBeenCalledWith("/optimize", {
      optimizer: "gepa",
      use_cache: true,
    });
  });

  it("optimizationApi.status gets /optimize/{jobId}", async () => {
    httpMock.get.mockResolvedValueOnce({ status: "running", message: "ok" });

    await optimizationApi.status("job-123");

    expect(httpMock.get).toHaveBeenCalledWith("/optimize/job-123");
  });

  it("evaluationApi.history gets /history with limit/offset", async () => {
    httpMock.get.mockResolvedValueOnce([]);

    await evaluationApi.history({ limit: 10, offset: 20 });

    expect(httpMock.get).toHaveBeenCalledWith("/history?limit=10&offset=20");
  });

  it("improvementApi.trigger posts to /self-improve", async () => {
    httpMock.post.mockResolvedValueOnce({ status: "completed", message: "ok" });

    await improvementApi.trigger({ min_quality: 8.5, max_examples: 5 });

    expect(httpMock.post).toHaveBeenCalledWith("/self-improve", {
      min_quality: 8.5,
      max_examples: 5,
    });
  });
});
