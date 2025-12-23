/**
 * Custom hook for Optimization Dashboard state management.
 *
 * Extracts all state, hooks, computed values, and handlers from the main component.
 */

import { useCallback, useMemo, useState } from "react";
import {
  useEvaluationHistory,
  useOptimizationRun,
  useOptimizationStatus,
  useDSPyConfig,
  useDSPyCacheInfo,
  useReasonerSummary,
  useDSPySignatures,
  useClearDSPyCache,
  useClearRoutingCache,
} from "@/api/hooks";

const HISTORY_LIMIT = 10;

export function useOptimizationDashboard() {
  // ----- State -----
  const [jobId, setJobId] = useState<string>("");
  const [historyOffset, setHistoryOffset] = useState(0);
  const [optimizer, setOptimizer] = useState<"bootstrap" | "gepa">("gepa");
  const [gepaPreset, setGepaPreset] = useState<"light" | "medium" | "heavy">(
    "light",
  );
  const [minQuality, setMinQuality] = useState("8.0");
  const [maxExamples, setMaxExamples] = useState("20");
  const [maxIterations, setMaxIterations] = useState("10"); // Default max iterations limit (lower to prevent long runs)
  const [harvestHistory, setHarvestHistory] = useState(true);
  const [historyHarvestLimit, setHistoryHarvestLimit] = useState("200");
  const [minQualityError, setMinQualityError] = useState<string | null>(null);
  const [maxExamplesError, setMaxExamplesError] = useState<string | null>(null);
  const [maxIterationsError, setMaxIterationsError] = useState<string | null>(
    null,
  );
  const [expandedSignatures, setExpandedSignatures] = useState<Set<string>>(
    new Set(),
  );

  // Validation function
  const validateInputs = useCallback((): boolean => {
    let isValid = true;

    // Validate minQuality (should be a number between 0 and 10)
    const minQualityNum = Number(minQuality);
    if (isNaN(minQualityNum) || minQuality.trim() === "") {
      setMinQualityError("Must be a valid number");
      isValid = false;
    } else if (minQualityNum < 0 || minQualityNum > 10) {
      setMinQualityError("Must be between 0 and 10");
      isValid = false;
    } else {
      setMinQualityError(null);
    }

    // Validate maxExamples (should be a positive integer)
    const maxExamplesNum = Number(maxExamples);
    if (isNaN(maxExamplesNum) || maxExamples.trim() === "") {
      setMaxExamplesError("Must be a valid number");
      isValid = false;
    } else if (!Number.isInteger(maxExamplesNum) || maxExamplesNum < 1) {
      setMaxExamplesError("Must be a positive integer");
      isValid = false;
    } else {
      setMaxExamplesError(null);
    }

    // Validate maxIterations (should be a positive integer, optional)
    if (maxIterations.trim() !== "") {
      const maxIterationsNum = Number(maxIterations);
      if (isNaN(maxIterationsNum)) {
        setMaxIterationsError("Must be a valid number");
        isValid = false;
      } else if (!Number.isInteger(maxIterationsNum) || maxIterationsNum < 1) {
        setMaxIterationsError("Must be a positive integer");
        isValid = false;
      } else {
        setMaxIterationsError(null);
      }
    } else {
      setMaxIterationsError(null);
    }

    return isValid;
  }, [minQuality, maxExamples, maxIterations]);

  // ----- Hooks -----
  const optimizationRun = useOptimizationRun({
    onSuccess: (result) => {
      const nextJobId = result.job_id ?? "";
      if (nextJobId) setJobId(nextJobId);
    },
  });

  const optimizationStatus = useOptimizationStatus(jobId || null);

  const historyQuery = useEvaluationHistory(
    { limit: HISTORY_LIMIT, offset: historyOffset },
    { placeholderData: (previous) => previous ?? [] },
  );

  const selfImprove = {
    isPending: optimizationRun.isPending,
    isError: optimizationRun.isError,
    data: null as unknown,
  };

  // DSPy Management Hooks
  const dspyConfig = useDSPyConfig();
  const dspyCacheInfo = useDSPyCacheInfo();
  const reasonerSummary = useReasonerSummary();
  const dspySignatures = useDSPySignatures();
  const clearCache = useClearDSPyCache();
  const clearRoutingCache = useClearRoutingCache();

  // ----- Computed values -----
  // If we got a 404 error, treat as idle (job not found)
  const currentStatus =
    optimizationStatus.error &&
    (optimizationStatus.error as any)?.response?.status === 404
      ? "idle"
      : (optimizationStatus.data?.status ?? "idle");

  // Use progress message from API if available, otherwise fallback to status-based message
  const currentMessage = useMemo(() => {
    if (optimizationStatus.data?.error) {
      return `Error: ${optimizationStatus.data.error}`;
    }
    if (optimizationStatus.data?.progress_message) {
      return optimizationStatus.data.progress_message;
    }
    switch (currentStatus) {
      case "completed":
        return "Optimization completed";
      case "running":
      case "started":
        return "Optimization in progress...";
      case "pending":
        return "Job queued, waiting to start...";
      case "failed":
        return "Optimization failed";
      default:
        return "Ready to optimize";
    }
  }, [
    currentStatus,
    optimizationStatus.data?.error,
    optimizationStatus.data?.progress_message,
  ]);

  // Use actual progress from API if available, otherwise estimate based on status
  const currentProgress = useMemo(() => {
    // Prefer explicit progress_percent from API
    if (
      optimizationStatus.data?.progress_percent !== undefined &&
      optimizationStatus.data.progress_percent !== null
    ) {
      return optimizationStatus.data.progress_percent;
    }
    // Fallback to status-based estimation
    switch (currentStatus) {
      case "completed":
        return 100;
      case "running":
      case "started":
        return 50;
      case "pending":
        return 10;
      case "failed":
        return 100;
      default:
        return 0;
    }
  }, [currentStatus, optimizationStatus.data?.progress_percent]);

  const ringStatus = useMemo(() => {
    if (currentStatus === "started" || currentStatus === "running")
      return "running";
    if (currentStatus === "completed") return "completed";
    if (currentStatus === "failed") return "failed";
    return "idle";
  }, [currentStatus]);

  // Calculate stats from history data and reasoner summary
  const selfImproveStats = useMemo(() => {
    const threshold = Number(minQuality);

    // Use reasoner summary for total count (accurate total)
    const totalExecutions = reasonerSummary.data?.history_count ?? 0;

    // Use history query data for quality calculations (sample-based)
    const entries = historyQuery.data ?? [];
    const scores = entries
      .map((e) => e.quality?.score)
      .filter((s): s is number => typeof s === "number" && !isNaN(s));

    // Calculate quality metrics from available history entries
    const highQuality = scores.filter((s) => s >= threshold).length;
    const avgScore =
      scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;

    // Calculate distribution
    const distribution = {
      High: scores.filter((s) => s >= 9).length,
      Medium: scores.filter((s) => s >= 7 && s < 9).length,
      Low: scores.filter((s) => s < 7).length,
    };

    // Potential examples are entries that meet quality threshold
    const potentialExamples = entries.filter(
      (e) => e.quality?.score && e.quality.score >= threshold,
    ).length;

    // If we have no data at all, return undefined to show "—"
    if (totalExecutions === 0 && entries.length === 0) {
      return undefined;
    }

    return {
      total_executions: totalExecutions,
      high_quality_executions: highQuality,
      potential_new_examples: potentialExamples,
      min_quality_threshold: threshold,
      average_quality_score: avgScore > 0 ? avgScore : undefined,
      quality_score_distribution: distribution,
    };
  }, [historyQuery.data, reasonerSummary.data, minQuality]);

  const isOptimizing =
    currentStatus === "started" || currentStatus === "running";

  // ----- Handlers -----
  const handleStartOptimization = useCallback(() => {
    if (!validateInputs()) {
      return;
    }
    optimizationRun.mutate({
      module_name: "DSPyReasoner",
      user_id: "default_user",
      auto_mode: gepaPreset,
      use_history_examples: harvestHistory,
      history_min_quality: harvestHistory ? Number(minQuality) : undefined,
      history_limit: harvestHistory ? Number(historyHarvestLimit) : undefined,
      options: {
        optimizer,
        max_iterations: maxIterations.trim()
          ? Number(maxIterations)
          : undefined,
      },
    });
  }, [
    optimizer,
    gepaPreset,
    harvestHistory,
    minQuality,
    optimizationRun,
    validateInputs,
  ]);

  const handleTriggerSelfImprove = useCallback(
    (statsOnly: boolean) => {
      if (!validateInputs()) {
        return;
      }
      optimizationRun.mutate({
        module_name: "DSPyReasoner",
        user_id: "default_user",
        auto_mode: gepaPreset,
        options: {
          min_quality: Number(minQuality),
          max_examples: Number(maxExamples),
          stats_only: statsOnly,
          is_self_improvement: true,
        },
      });
    },
    [minQuality, maxExamples, gepaPreset, optimizationRun, validateInputs],
  );

  const handleClearCache = useCallback(() => {
    clearCache.mutate();
  }, [clearCache]);

  const handleClearRoutingCache = useCallback(() => {
    clearRoutingCache.mutate();
  }, [clearRoutingCache]);

  const toggleSignature = useCallback((name: string) => {
    setExpandedSignatures((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  const formatBytes = useCallback((bytes?: number): string => {
    if (bytes === undefined || bytes === null) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }, []);

  return {
    // State
    jobId,
    setJobId,
    historyOffset,
    setHistoryOffset,
    historyLimit: HISTORY_LIMIT,
    optimizer,
    setOptimizer,
    gepaPreset,
    setGepaPreset,
    minQuality,
    setMinQuality,
    maxExamples,
    setMaxExamples,
    maxIterations,
    setMaxIterations,
    harvestHistory,
    setHarvestHistory,
    historyHarvestLimit,
    setHistoryHarvestLimit,
    minQualityError,
    setMinQualityError,
    maxExamplesError,
    setMaxExamplesError,
    maxIterationsError,
    setMaxIterationsError,
    expandedSignatures,
    // Hooks
    optimizationRun,
    optimizationStatus,
    historyQuery,
    selfImprove,
    dspyConfig,
    dspyCacheInfo,
    reasonerSummary,
    dspySignatures,
    clearCache,
    clearRoutingCache,
    // Computed
    currentStatus,
    currentMessage,
    currentProgress,
    ringStatus,
    selfImproveStats,
    isOptimizing,
    // Handlers
    handleStartOptimization,
    handleTriggerSelfImprove,
    handleClearCache,
    handleClearRoutingCache,
    toggleSignature,
    formatBytes,
    validateInputs,
  };
}
