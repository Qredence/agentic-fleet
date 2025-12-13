import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  useEvaluationHistory,
  useOptimizationRun,
  useOptimizationStatus,
  useTriggerSelfImprove,
} from "@/api/hooks";

function formatMaybeDate(value: unknown): string {
  if (typeof value !== "string") return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function OptimizationDashboard() {
  const [jobId, setJobId] = useState<string>("");
  const [historyOffset, setHistoryOffset] = useState(0);
  const historyLimit = 20;

  const [minQuality, setMinQuality] = useState("8.0");
  const [maxExamples, setMaxExamples] = useState("20");

  const optimizationRun = useOptimizationRun({
    onSuccess: (result) => {
      const nextJobId = result.job_id ?? "";
      if (nextJobId) setJobId(nextJobId);
    },
  });

  const optimizationStatus = useOptimizationStatus(jobId || null);

  const historyQuery = useEvaluationHistory(
    { limit: historyLimit, offset: historyOffset },
    { placeholderData: (previous) => previous ?? [] },
  );

  const selfImprove = useTriggerSelfImprove();

  const statusText = useMemo(() => {
    if (!jobId) return "No job running.";
    if (optimizationStatus.isLoading) return "Loading job status…";
    if (optimizationStatus.isError) return "Failed to load job status.";
    if (!optimizationStatus.data) return "No status available.";
    return `${optimizationStatus.data.status}: ${optimizationStatus.data.message}`;
  }, [
    jobId,
    optimizationStatus.data,
    optimizationStatus.isError,
    optimizationStatus.isLoading,
  ]);

  return (
    <div className="flex h-full w-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
        <div>
          <div className="text-lg font-semibold tracking-tight">
            Optimization Dashboard
          </div>
          <div className="text-sm text-muted-foreground">
            Launch optimization runs, monitor progress, and review evaluation
            history.
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-6">
        <div className="mx-auto w-full max-w-4xl space-y-8">
          <section className="rounded-lg border border-border bg-card/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-medium">Run optimization</div>
                <div className="text-sm text-muted-foreground">
                  Starts a background optimization job (GEPA/bootstrap).
                </div>
              </div>
              <Button
                onClick={() =>
                  optimizationRun.mutate({
                    optimizer: "gepa",
                    use_cache: true,
                    gepa_auto: "light",
                    harvest_history: true,
                    min_quality: Number(minQuality) || 8.0,
                  })
                }
                disabled={optimizationRun.isPending}
                aria-label="Start optimization run"
              >
                {optimizationRun.isPending ? "Starting…" : "Start run"}
              </Button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <div className="mb-1 text-muted-foreground">Job ID</div>
                <Input
                  value={jobId}
                  onChange={(e) => setJobId(e.target.value)}
                  placeholder="job id (for status polling)"
                />
              </label>
              <div className="text-sm">
                <div className="mb-1 text-muted-foreground">Status</div>
                <div className="rounded-md border border-border bg-muted/20 p-2">
                  {statusText}
                </div>
              </div>
            </div>

            {optimizationRun.isError ? (
              <div className="mt-3 text-sm text-destructive">
                Failed to start optimization.
              </div>
            ) : null}
          </section>

          <section className="rounded-lg border border-border bg-card/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-medium">Self-improve</div>
                <div className="text-sm text-muted-foreground">
                  Generate training examples from high-quality history.
                </div>
              </div>
              <Button
                onClick={() =>
                  selfImprove.mutate({
                    min_quality: Number(minQuality) || 8.0,
                    max_examples: Number(maxExamples) || 20,
                    stats_only: false,
                  })
                }
                disabled={selfImprove.isPending}
                aria-label="Trigger self-improvement"
              >
                {selfImprove.isPending ? "Running…" : "Trigger"}
              </Button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <div className="mb-1 text-muted-foreground">Min quality</div>
                <Input
                  inputMode="decimal"
                  value={minQuality}
                  onChange={(e) => setMinQuality(e.target.value)}
                />
              </label>
              <label className="text-sm">
                <div className="mb-1 text-muted-foreground">Max examples</div>
                <Input
                  inputMode="numeric"
                  value={maxExamples}
                  onChange={(e) => setMaxExamples(e.target.value)}
                />
              </label>
            </div>

            {selfImprove.isError ? (
              <div className="mt-3 text-sm text-destructive">
                Self-improvement failed.
              </div>
            ) : null}

            {selfImprove.data ? (
              <div className="mt-3">
                <div className="text-sm text-muted-foreground">Result</div>
                <Textarea
                  readOnly
                  value={JSON.stringify(selfImprove.data, null, 2)}
                  className="mt-1 min-h-24"
                />
              </div>
            ) : null}
          </section>

          <section className="rounded-lg border border-border bg-card/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-medium">Evaluation history</div>
                <div className="text-sm text-muted-foreground">
                  Recent executions with quality metrics (when available).
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() =>
                    setHistoryOffset((v) => Math.max(0, v - historyLimit))
                  }
                  disabled={historyOffset === 0 || historyQuery.isFetching}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setHistoryOffset((v) => v + historyLimit)}
                  disabled={historyQuery.isFetching}
                >
                  Next
                </Button>
              </div>
            </div>

            <Separator className="my-4" />

            {historyQuery.isLoading ? (
              <div className="text-sm text-muted-foreground">Loading…</div>
            ) : historyQuery.isError ? (
              <div className="text-sm text-destructive">
                Failed to load history.
              </div>
            ) : historyQuery.data?.length ? (
              <div className="space-y-3">
                {historyQuery.data.map((entry) => {
                  const workflowId =
                    (entry.workflowId as string | undefined) ??
                    (entry.workflow_id as string | undefined) ??
                    "unknown";
                  const task =
                    typeof entry.task === "string" ? entry.task : "(no task)";
                  const score =
                    typeof entry.quality?.score === "number"
                      ? entry.quality.score.toFixed(1)
                      : "n/a";
                  const flag =
                    typeof entry.quality?.flag === "string"
                      ? entry.quality.flag
                      : "";
                  const status =
                    typeof entry.status === "string" ? entry.status : "";

                  return (
                    <div
                      key={workflowId}
                      className="rounded-md border border-border bg-muted/10 p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-sm font-medium">{workflowId}</div>
                        <div className="text-xs text-muted-foreground">
                          {status ? `${status} • ` : ""}
                          score: {score}
                          {flag ? ` • ${flag}` : ""}
                        </div>
                      </div>
                      <div className="mt-2 text-sm text-muted-foreground">
                        {task}
                      </div>
                      <div className="mt-2 text-xs text-muted-foreground">
                        {formatMaybeDate(
                          entry.completed_at || entry.completedAt,
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                No history entries found.
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
