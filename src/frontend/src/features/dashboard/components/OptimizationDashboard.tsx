import { useCallback, useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Separator } from "@/shared/components/ui/separator";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Progress } from "@/shared/components/ui/progress";
import { Badge } from "@/shared/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs";
import { TextShimmer } from "@/features/chat/components/text-shimmer";
import {
  useEvaluationHistory,
  useOptimizationRun,
  useOptimizationStatus,
  useTriggerSelfImprove,
  useDSPyConfig,
  useDSPyCacheInfo,
  useReasonerSummary,
  useDSPySignatures,
  useClearDSPyCache,
  useClearRoutingCache,
} from "@/api/hooks";
import type { SelfImproveStats, HistoryExecutionEntry } from "@/api/types";
import { cn } from "@/shared/lib/utils";
import {
  Activity,
  Zap,
  Database,
  TrendingUp,
  Play,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Sparkles,
  BarChart3,
  History,
  ChevronLeft,
  ChevronRight,
  Settings2,
  Target,
  Layers,
  Cpu,
  BrainCircuit,
  Trash2,
  HardDrive,
  FileCode,
  Hash,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// ============================================================================
// Animation Variants
// ============================================================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
} as const;

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 300,
      damping: 24,
    },
  },
} as const;

const pulseVariants = {
  idle: { scale: 1 },
  active: {
    scale: [1, 1.05, 1] as number[],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut" as const,
    },
  },
};

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const variant = useMemo(() => {
    switch (status) {
      case "completed":
      case "cached":
        return "success";
      case "running":
      case "started":
        return "info";
      case "failed":
        return "destructive";
      default:
        return "secondary";
    }
  }, [status]);

  return (
    <Badge variant={variant} className="font-mono text-xs uppercase">
      {status}
    </Badge>
  );
}

// ============================================================================
// Stat Card Component
// ============================================================================

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  description?: string;
}

function StatCard({ label, value, icon, description }: StatCardProps) {
  return (
    <motion.div variants={itemVariants}>
      <Card className="relative overflow-hidden">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-muted-foreground text-sm font-medium">
                {label}
              </p>
              <p className="font-mono text-2xl font-bold tabular-nums">
                {value}
              </p>
              {description && (
                <p className="text-muted-foreground text-xs">{description}</p>
              )}
            </div>
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              {icon}
            </div>
          </div>
        </CardContent>
        {/* Decorative gradient */}
        <div className="from-primary/5 pointer-events-none absolute inset-0 bg-gradient-to-br to-transparent" />
      </Card>
    </motion.div>
  );
}

// ============================================================================
// Progress Ring Component (SVG-based)
// ============================================================================

interface ProgressRingProps {
  progress: number;
  status: "idle" | "running" | "completed" | "failed";
}

function ProgressRing({ progress, status }: ProgressRingProps) {
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  const statusColors = useMemo(
    () => ({
      idle: { stroke: "stroke-muted", fill: "text-muted-foreground" },
      running: { stroke: "stroke-blue-500", fill: "text-blue-500" },
      completed: { stroke: "stroke-green-500", fill: "text-green-500" },
      failed: { stroke: "stroke-red-500", fill: "text-red-500" },
    }),
    [],
  );

  const { stroke, fill } = statusColors[status];

  return (
    <motion.div
      className="relative"
      variants={pulseVariants}
      animate={status === "running" ? "active" : "idle"}
    >
      <svg width={size} height={size} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted/30"
        />
        {/* Progress arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeLinecap="round"
          className={cn(stroke, "transition-colors duration-300")}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("font-mono text-2xl font-bold tabular-nums", fill)}>
          {Math.round(progress)}%
        </span>
        <span className="text-muted-foreground text-xs uppercase tracking-wider">
          {status}
        </span>
      </div>
    </motion.div>
  );
}

// ============================================================================
// Quality Distribution Chart
// ============================================================================

interface QualityChartProps {
  distribution: Record<string, number>;
}

function QualityChart({ distribution }: QualityChartProps) {
  const entries = Object.entries(distribution);
  const maxValue = Math.max(...entries.map(([, v]) => v), 1);

  const barColors = [
    "bg-green-500",
    "bg-blue-500",
    "bg-orange-500",
    "bg-red-500",
  ];

  return (
    <div className="space-y-3">
      {entries.map(([label, count], index) => (
        <div key={label}>
          <div className="text-muted-foreground mb-1 flex items-center justify-between text-xs">
            <span>{label}</span>
            <span className="font-mono tabular-nums">{count}</span>
          </div>
          <div className="bg-muted h-2 overflow-hidden rounded-full">
            <motion.div
              className={cn("h-full", barColors[index % barColors.length])}
              initial={{ width: 0 }}
              animate={{ width: `${(count / maxValue) * 100}%` }}
              transition={{
                duration: 0.5,
                delay: index * 0.1,
                ease: "easeOut",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// History Entry Component
// ============================================================================

interface HistoryEntryProps {
  entry: HistoryExecutionEntry;
  index: number;
}

function HistoryEntry({ entry, index }: HistoryEntryProps) {
  const workflowId = entry.workflowId ?? entry.workflow_id ?? "unknown";
  const task = typeof entry.task === "string" ? entry.task : "(no task)";
  const score =
    typeof entry.quality?.score === "number"
      ? entry.quality.score.toFixed(1)
      : "—";
  const status = typeof entry.status === "string" ? entry.status : "unknown";

  const scoreNum = entry.quality?.score;
  const scoreBadgeVariant = useMemo(() => {
    if (scoreNum === undefined) return "secondary";
    if (scoreNum >= 9) return "success";
    if (scoreNum >= 8) return "info";
    if (scoreNum >= 7) return "warning";
    return "destructive";
  }, [scoreNum]);

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="hover:bg-muted/50 group flex items-start gap-3 rounded-lg p-3 transition-colors"
    >
      {/* Status indicator */}
      <div
        className={cn(
          "mt-1.5 h-2 w-2 shrink-0 rounded-full",
          status === "completed"
            ? "bg-green-500"
            : status === "failed"
              ? "bg-red-500"
              : status === "running"
                ? "animate-pulse bg-blue-500"
                : "bg-muted-foreground",
        )}
      />

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p
          className="text-foreground truncate text-sm font-medium"
          title={task}
        >
          {task}
        </p>
        <div className="text-muted-foreground mt-1 flex flex-wrap items-center gap-2 text-xs">
          <code className="bg-muted rounded px-1.5 py-0.5 font-mono">
            {workflowId.slice(0, 8)}
          </code>
          {entry.mode && (
            <Badge variant="outline" className="text-xs">
              {entry.mode}
            </Badge>
          )}
        </div>
      </div>

      {/* Score */}
      <Badge variant={scoreBadgeVariant} className="shrink-0 font-mono">
        {score}
      </Badge>
    </motion.div>
  );
}

// ============================================================================
// Optimizer Selector Component
// ============================================================================

interface OptimizerSelectorProps {
  value: "bootstrap" | "gepa";
  onChange: (value: "bootstrap" | "gepa") => void;
  disabled?: boolean;
}

function OptimizerSelector({
  value,
  onChange,
  disabled,
}: OptimizerSelectorProps) {
  return (
    <div className="flex gap-2">
      {(["bootstrap", "gepa"] as const).map((opt) => (
        <Button
          key={opt}
          type="button"
          variant={value === opt ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(opt)}
          disabled={disabled}
          className="flex-1"
        >
          {opt === "bootstrap" ? (
            <Layers className="mr-1.5 size-4" />
          ) : (
            <Cpu className="mr-1.5 size-4" />
          )}
          {opt.charAt(0).toUpperCase() + opt.slice(1)}
        </Button>
      ))}
    </div>
  );
}

// ============================================================================
// GEPA Preset Selector Component
// ============================================================================

interface GepaPresetSelectorProps {
  value: "light" | "medium" | "heavy";
  onChange: (value: "light" | "medium" | "heavy") => void;
  disabled?: boolean;
}

function GepaPresetSelector({
  value,
  onChange,
  disabled,
}: GepaPresetSelectorProps) {
  const presets = [
    { value: "light" as const, label: "Light", desc: "Fast, lower cost" },
    { value: "medium" as const, label: "Medium", desc: "Balanced" },
    { value: "heavy" as const, label: "Heavy", desc: "Thorough, higher cost" },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {presets.map((preset) => (
        <Button
          key={preset.value}
          type="button"
          variant={value === preset.value ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(preset.value)}
          disabled={disabled}
          className="flex-col py-3"
        >
          <span>{preset.label}</span>
          <span className="text-[10px] font-normal opacity-70">
            {preset.desc}
          </span>
        </Button>
      ))}
    </div>
  );
}

// ============================================================================
// Main Optimization Dashboard Component
// ============================================================================

export function OptimizationDashboard() {
  // ----- State -----
  const [jobId, setJobId] = useState<string>("");
  const [historyOffset, setHistoryOffset] = useState(0);
  const historyLimit = 10;

  const [optimizer, setOptimizer] = useState<"bootstrap" | "gepa">("gepa");
  const [gepaPreset, setGepaPreset] = useState<"light" | "medium" | "heavy">(
    "light",
  );
  const [minQuality, setMinQuality] = useState("8.0");
  const [maxExamples, setMaxExamples] = useState("20");
  const [harvestHistory, setHarvestHistory] = useState(true);

  // ----- Hooks -----
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

  // DSPy Management Hooks
  const dspyConfig = useDSPyConfig();
  const dspyCacheInfo = useDSPyCacheInfo();
  const reasonerSummary = useReasonerSummary();
  const dspySignatures = useDSPySignatures();
  const clearCache = useClearDSPyCache();
  const clearRoutingCache = useClearRoutingCache();

  // Signatures expanded state
  const [expandedSignatures, setExpandedSignatures] = useState<Set<string>>(
    new Set(),
  );

  // ----- Computed values -----
  const currentStatus = optimizationStatus.data?.status ?? "idle";
  const currentMessage =
    optimizationStatus.data?.message ?? "Ready to optimize";
  const currentProgress = (optimizationStatus.data?.progress ?? 0) * 100;

  const ringStatus = useMemo(() => {
    if (currentStatus === "started" || currentStatus === "running")
      return "running";
    if (currentStatus === "completed" || currentStatus === "cached")
      return "completed";
    if (currentStatus === "failed") return "failed";
    return "idle";
  }, [currentStatus]);

  const selfImproveStats: SelfImproveStats | undefined =
    selfImprove.data?.stats;
  const isOptimizing =
    currentStatus === "started" || currentStatus === "running";

  // ----- Handlers -----
  const handleStartOptimization = useCallback(() => {
    optimizationRun.mutate({
      optimizer,
      use_cache: true,
      gepa_auto: optimizer === "gepa" ? gepaPreset : null,
      harvest_history: harvestHistory,
      min_quality: Number(minQuality) || 8.0,
    });
  }, [optimizer, gepaPreset, harvestHistory, minQuality, optimizationRun]);

  const handleTriggerSelfImprove = useCallback(
    (statsOnly: boolean) => {
      selfImprove.mutate({
        min_quality: Number(minQuality) || 8.0,
        max_examples: Number(maxExamples) || 20,
        stats_only: statsOnly,
      });
    },
    [minQuality, maxExamples, selfImprove],
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

  // Helper to format bytes
  const formatBytes = useCallback((bytes?: number): string => {
    if (bytes === undefined || bytes === null) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="bg-background flex h-full w-full flex-col">
      {/* Header */}
      <div className="border-border border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-foreground text-xl font-semibold tracking-tight">
              Optimization Control
            </h1>
            <p className="text-muted-foreground mt-0.5 text-sm">
              DSPy compilation, self-improvement, and performance monitoring
            </p>
          </div>
          <StatusBadge status={currentStatus} />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <motion.div
          className="mx-auto max-w-6xl space-y-6 p-6"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Top Row: Progress + Quick Stats */}
          <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
            {/* Progress Card */}
            <motion.div variants={itemVariants}>
              <Card className="flex h-full flex-col items-center justify-center p-6">
                <ProgressRing progress={currentProgress} status={ringStatus} />
                <div className="mt-4 text-center">
                  <p className="text-foreground text-sm font-medium">
                    {isOptimizing ? (
                      <TextShimmer duration={2}>Compiling...</TextShimmer>
                    ) : (
                      "Job Progress"
                    )}
                  </p>
                  <p className="text-muted-foreground mt-1 font-mono text-xs">
                    {jobId ? `${jobId.slice(0, 12)}...` : "No active job"}
                  </p>
                </div>
              </Card>
            </motion.div>

            {/* Stats Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard
                label="Total Executions"
                value={selfImproveStats?.total_executions ?? "—"}
                icon={<Activity className="size-5" />}
              />
              <StatCard
                label="High Quality"
                value={selfImproveStats?.high_quality_executions ?? "—"}
                icon={<Sparkles className="size-5" />}
                description="Score ≥ threshold"
              />
              <StatCard
                label="Avg. Score"
                value={
                  selfImproveStats?.average_quality_score !== undefined
                    ? selfImproveStats.average_quality_score.toFixed(1)
                    : "—"
                }
                icon={<Target className="size-5" />}
              />
              <StatCard
                label="Potential Examples"
                value={selfImproveStats?.potential_new_examples ?? "—"}
                icon={<Database className="size-5" />}
              />
              <StatCard
                label="Quality Threshold"
                value={selfImproveStats?.min_quality_threshold ?? minQuality}
                icon={<TrendingUp className="size-5" />}
              />
              <StatCard
                label="Examples Added"
                value={selfImprove.data?.new_examples_added ?? 0}
                icon={<Zap className="size-5" />}
              />
            </div>
          </div>

          {/* Tabs Section */}
          <Tabs defaultValue="optimize" className="space-y-4">
            <TabsList>
              <TabsTrigger value="optimize">
                <Settings2 className="mr-1.5 size-4" />
                Optimize
              </TabsTrigger>
              <TabsTrigger value="self-improve">
                <Sparkles className="mr-1.5 size-4" />
                Self-Improve
              </TabsTrigger>
              <TabsTrigger value="dspy">
                <BrainCircuit className="mr-1.5 size-4" />
                DSPy
              </TabsTrigger>
              <TabsTrigger value="history">
                <History className="mr-1.5 size-4" />
                History
              </TabsTrigger>
            </TabsList>

            {/* Optimize Tab */}
            <TabsContent value="optimize">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Configuration */}
                <motion.div variants={itemVariants}>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Settings2 className="size-5" />
                        Configuration
                      </CardTitle>
                      <CardDescription>
                        Configure the optimization parameters
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Optimizer */}
                      <div>
                        <label className="text-muted-foreground mb-2 block text-sm font-medium">
                          Optimizer
                        </label>
                        <OptimizerSelector
                          value={optimizer}
                          onChange={setOptimizer}
                          disabled={isOptimizing}
                        />
                      </div>

                      {/* GEPA Preset */}
                      <AnimatePresence mode="wait">
                        {optimizer === "gepa" && (
                          <motion.div
                            key="gepa-preset"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <label className="text-muted-foreground mb-2 block text-sm font-medium">
                              GEPA Preset
                            </label>
                            <GepaPresetSelector
                              value={gepaPreset}
                              onChange={setGepaPreset}
                              disabled={isOptimizing}
                            />
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Min Quality + Harvest */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-muted-foreground mb-2 block text-sm font-medium">
                            Min Quality
                          </label>
                          <Input
                            inputMode="decimal"
                            value={minQuality}
                            onChange={(e) => setMinQuality(e.target.value)}
                            disabled={isOptimizing}
                            placeholder="8.0"
                          />
                        </div>
                        <div>
                          <label className="text-muted-foreground mb-2 block text-sm font-medium">
                            Harvest History
                          </label>
                          <Button
                            type="button"
                            variant={harvestHistory ? "default" : "outline"}
                            className="w-full"
                            onClick={() => setHarvestHistory(!harvestHistory)}
                            disabled={isOptimizing}
                          >
                            {harvestHistory ? "Enabled" : "Disabled"}
                          </Button>
                        </div>
                      </div>

                      <Separator />

                      {/* Start Button */}
                      <Button
                        onClick={handleStartOptimization}
                        disabled={optimizationRun.isPending || isOptimizing}
                        className="w-full"
                        size="lg"
                      >
                        {optimizationRun.isPending ? (
                          <>
                            <Loader2 className="mr-2 size-4 animate-spin" />
                            Starting...
                          </>
                        ) : isOptimizing ? (
                          <>
                            <RefreshCw className="mr-2 size-4 animate-spin" />
                            Running...
                          </>
                        ) : (
                          <>
                            <Play className="mr-2 size-4" />
                            Start Optimization
                          </>
                        )}
                      </Button>

                      {optimizationRun.isError && (
                        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">
                          <XCircle className="size-4" />
                          Failed to start optimization
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Status */}
                <motion.div variants={itemVariants}>
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="size-5" />
                        Status
                      </CardTitle>
                      <CardDescription>
                        Current optimization job status
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Job ID Input */}
                      <div>
                        <label className="text-muted-foreground mb-2 block text-sm font-medium">
                          Job ID
                        </label>
                        <Input
                          value={jobId}
                          onChange={(e) => setJobId(e.target.value)}
                          placeholder="Enter job ID to track"
                          className="font-mono"
                        />
                      </div>

                      {/* Status Display */}
                      <div className="bg-muted/50 space-y-3 rounded-lg border p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground text-sm">
                            Status
                          </span>
                          <StatusBadge status={currentStatus} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground text-sm">
                            Progress
                          </span>
                          <span className="font-mono text-sm">
                            {Math.round(currentProgress)}%
                          </span>
                        </div>
                        <Progress value={currentProgress} className="h-2" />
                        <p className="text-muted-foreground text-xs">
                          {currentMessage}
                        </p>
                      </div>

                      {/* Timestamps */}
                      {optimizationStatus.data?.started_at && (
                        <div className="text-muted-foreground space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span>Started</span>
                            <span className="font-mono">
                              {new Date(
                                optimizationStatus.data.started_at,
                              ).toLocaleString()}
                            </span>
                          </div>
                          {optimizationStatus.data?.completed_at && (
                            <div className="flex justify-between">
                              <span>Completed</span>
                              <span className="font-mono">
                                {new Date(
                                  optimizationStatus.data.completed_at,
                                ).toLocaleString()}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </TabsContent>

            {/* Self-Improve Tab */}
            <TabsContent value="self-improve">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Controls */}
                <motion.div variants={itemVariants}>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Sparkles className="size-5" />
                        Self-Improvement
                      </CardTitle>
                      <CardDescription>
                        Generate training examples from high-quality history
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Parameters */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-muted-foreground mb-2 block text-sm font-medium">
                            Min Quality
                          </label>
                          <Input
                            inputMode="decimal"
                            value={minQuality}
                            onChange={(e) => setMinQuality(e.target.value)}
                            disabled={selfImprove.isPending}
                          />
                        </div>
                        <div>
                          <label className="text-muted-foreground mb-2 block text-sm font-medium">
                            Max Examples
                          </label>
                          <Input
                            inputMode="numeric"
                            value={maxExamples}
                            onChange={(e) => setMaxExamples(e.target.value)}
                            disabled={selfImprove.isPending}
                          />
                        </div>
                      </div>

                      <Separator />

                      {/* Actions */}
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          onClick={() => handleTriggerSelfImprove(true)}
                          disabled={selfImprove.isPending}
                          className="flex-1"
                        >
                          {selfImprove.isPending ? (
                            <Loader2 className="mr-2 size-4 animate-spin" />
                          ) : (
                            <BarChart3 className="mr-2 size-4" />
                          )}
                          Preview Stats
                        </Button>
                        <Button
                          onClick={() => handleTriggerSelfImprove(false)}
                          disabled={selfImprove.isPending}
                          className="flex-1"
                        >
                          {selfImprove.isPending ? (
                            <Loader2 className="mr-2 size-4 animate-spin" />
                          ) : (
                            <Zap className="mr-2 size-4" />
                          )}
                          Generate
                        </Button>
                      </div>

                      {/* Result Message */}
                      <AnimatePresence mode="wait">
                        {selfImprove.data && (
                          <motion.div
                            key="result"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className={cn(
                              "flex items-start gap-2 rounded-lg p-3 text-sm",
                              selfImprove.data.status === "completed"
                                ? "bg-green-500/10 text-green-500"
                                : selfImprove.data.status === "no_op"
                                  ? "bg-orange-500/10 text-orange-500"
                                  : "bg-red-500/10 text-red-500",
                            )}
                          >
                            {selfImprove.data.status === "completed" ? (
                              <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                            ) : selfImprove.data.status === "no_op" ? (
                              <Clock className="mt-0.5 size-4 shrink-0" />
                            ) : (
                              <XCircle className="mt-0.5 size-4 shrink-0" />
                            )}
                            <span>{selfImprove.data.message}</span>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {selfImprove.isError && (
                        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">
                          <XCircle className="size-4" />
                          Self-improvement failed
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Quality Distribution */}
                <motion.div variants={itemVariants}>
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="size-5" />
                        Quality Distribution
                      </CardTitle>
                      <CardDescription>
                        Score distribution across executions
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {selfImproveStats?.quality_score_distribution ? (
                        <QualityChart
                          distribution={
                            selfImproveStats.quality_score_distribution
                          }
                        />
                      ) : (
                        <div className="text-muted-foreground flex h-32 flex-col items-center justify-center text-sm">
                          <BarChart3 className="mb-2 size-8 opacity-30" />
                          <p>Click "Preview Stats" to load distribution</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </TabsContent>

            {/* DSPy Tab */}
            <TabsContent value="dspy">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Configuration & Status */}
                <motion.div variants={itemVariants}>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BrainCircuit className="size-5" />
                        DSPy Configuration
                      </CardTitle>
                      <CardDescription>
                        Current DSPy setup and reasoner status
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Config Section */}
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium">Language Model</h4>
                        <div className="bg-muted/50 rounded-lg border p-3">
                          {dspyConfig.isLoading ? (
                            <div className="flex items-center gap-2 text-sm">
                              <Loader2 className="size-4 animate-spin" />
                              Loading config...
                            </div>
                          ) : dspyConfig.isError ? (
                            <div className="flex items-center gap-2 text-sm text-red-500">
                              <AlertTriangle className="size-4" />
                              Failed to load config
                            </div>
                          ) : (
                            <div className="space-y-2 text-sm">
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">
                                  Provider
                                </span>
                                <code className="bg-muted rounded px-2 py-0.5 font-mono text-xs">
                                  {dspyConfig.data?.lm_provider ?? "—"}
                                </code>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">
                                  Adapter
                                </span>
                                <code className="bg-muted rounded px-2 py-0.5 font-mono text-xs">
                                  {dspyConfig.data?.adapter ?? "default"}
                                </code>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Reasoner Status */}
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium">Reasoner Status</h4>
                        <div className="bg-muted/50 rounded-lg border p-3">
                          {reasonerSummary.isLoading ? (
                            <div className="flex items-center gap-2 text-sm">
                              <Loader2 className="size-4 animate-spin" />
                              Loading...
                            </div>
                          ) : reasonerSummary.isError ? (
                            <div className="flex items-center gap-2 text-sm text-red-500">
                              <AlertTriangle className="size-4" />
                              Failed to load reasoner
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div className="flex flex-col gap-1">
                                <span className="text-muted-foreground text-xs">
                                  Modules
                                </span>
                                <Badge
                                  variant={
                                    reasonerSummary.data?.modules_initialized
                                      ? "success"
                                      : "secondary"
                                  }
                                  className="w-fit"
                                >
                                  {reasonerSummary.data?.modules_initialized
                                    ? "Initialized"
                                    : "Not Ready"}
                                </Badge>
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-muted-foreground text-xs">
                                  Typed Signatures
                                </span>
                                <Badge
                                  variant={
                                    reasonerSummary.data?.use_typed_signatures
                                      ? "success"
                                      : "secondary"
                                  }
                                  className="w-fit"
                                >
                                  {reasonerSummary.data?.use_typed_signatures
                                    ? "Enabled"
                                    : "Disabled"}
                                </Badge>
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-muted-foreground text-xs">
                                  History Count
                                </span>
                                <span className="font-mono">
                                  {reasonerSummary.data?.history_count ?? 0}
                                </span>
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-muted-foreground text-xs">
                                  Routing Cache
                                </span>
                                <span className="font-mono">
                                  {reasonerSummary.data?.routing_cache_size ??
                                    0}{" "}
                                  entries
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      <Separator />

                      {/* Clear Routing Cache */}
                      <Button
                        variant="outline"
                        onClick={handleClearRoutingCache}
                        disabled={clearRoutingCache.isPending}
                        className="w-full"
                      >
                        {clearRoutingCache.isPending ? (
                          <Loader2 className="mr-2 size-4 animate-spin" />
                        ) : (
                          <Trash2 className="mr-2 size-4" />
                        )}
                        Clear Routing Cache
                      </Button>

                      {clearRoutingCache.isSuccess && (
                        <div className="flex items-center gap-2 rounded-lg bg-green-500/10 px-3 py-2 text-sm text-green-500">
                          <CheckCircle2 className="size-4" />
                          Routing cache cleared
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Cache Info */}
                <motion.div variants={itemVariants}>
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <HardDrive className="size-5" />
                        Compilation Cache
                      </CardTitle>
                      <CardDescription>
                        DSPy compiled module cache status
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {dspyCacheInfo.isLoading ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="mr-2 size-4 animate-spin" />
                          Loading cache info...
                        </div>
                      ) : dspyCacheInfo.isError ? (
                        <div className="flex items-center justify-center py-8 text-red-500">
                          <AlertTriangle className="mr-2 size-4" />
                          Failed to load cache info
                        </div>
                      ) : !dspyCacheInfo.data?.exists ? (
                        <div className="text-muted-foreground flex flex-col items-center justify-center py-8 text-sm">
                          <Database className="mb-2 size-8 opacity-30" />
                          <p>No compiled cache found</p>
                          <p className="text-xs opacity-70">
                            Run optimization to create cache
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="bg-muted/50 rounded-lg border p-4">
                            <div className="flex items-center gap-2 text-green-500">
                              <CheckCircle2 className="size-5" />
                              <span className="font-medium">
                                Cache Available
                              </span>
                            </div>
                            <div className="mt-3 grid gap-2 text-sm">
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">
                                  Created
                                </span>
                                <span className="font-mono text-xs">
                                  {dspyCacheInfo.data.created_at
                                    ? new Date(
                                        dspyCacheInfo.data.created_at,
                                      ).toLocaleString()
                                    : "—"}
                                </span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">
                                  Size
                                </span>
                                <span className="font-mono text-xs">
                                  {formatBytes(
                                    dspyCacheInfo.data.cache_size_bytes,
                                  )}
                                </span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">
                                  Optimizer
                                </span>
                                <Badge variant="outline" className="font-mono">
                                  {dspyCacheInfo.data.optimizer ?? "unknown"}
                                </Badge>
                              </div>
                              {dspyCacheInfo.data.signature_hash && (
                                <div className="flex items-center justify-between">
                                  <span className="text-muted-foreground">
                                    Signature Hash
                                  </span>
                                  <code className="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">
                                    {dspyCacheInfo.data.signature_hash.slice(
                                      0,
                                      8,
                                    )}
                                    ...
                                  </code>
                                </div>
                              )}
                            </div>
                          </div>

                          <Button
                            variant="destructive"
                            onClick={handleClearCache}
                            disabled={clearCache.isPending}
                            className="w-full"
                          >
                            {clearCache.isPending ? (
                              <Loader2 className="mr-2 size-4 animate-spin" />
                            ) : (
                              <Trash2 className="mr-2 size-4" />
                            )}
                            Clear Compilation Cache
                          </Button>

                          {clearCache.isSuccess && (
                            <div className="flex items-center gap-2 rounded-lg bg-green-500/10 px-3 py-2 text-sm text-green-500">
                              <CheckCircle2 className="size-4" />
                              Cache cleared successfully
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Signatures List */}
                <motion.div variants={itemVariants} className="lg:col-span-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileCode className="size-5" />
                        DSPy Signatures
                      </CardTitle>
                      <CardDescription>
                        Available signatures for routing, analysis, and quality
                        assessment
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {dspySignatures.isLoading ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="mr-2 size-4 animate-spin" />
                          Loading signatures...
                        </div>
                      ) : dspySignatures.isError ? (
                        <div className="flex items-center justify-center py-8 text-red-500">
                          <AlertTriangle className="mr-2 size-4" />
                          Failed to load signatures
                        </div>
                      ) : !dspySignatures.data ||
                        Object.keys(dspySignatures.data).length === 0 ? (
                        <div className="text-muted-foreground flex flex-col items-center justify-center py-8 text-sm">
                          <FileCode className="mb-2 size-8 opacity-30" />
                          <p>No signatures found</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {Object.entries(dspySignatures.data).map(
                            ([name, sig]) => (
                              <div
                                key={name}
                                className="border-border rounded-lg border"
                              >
                                <button
                                  type="button"
                                  onClick={() => toggleSignature(name)}
                                  className="hover:bg-muted/50 flex w-full items-center justify-between p-3 text-left transition-colors"
                                >
                                  <div className="flex items-center gap-2">
                                    <Hash className="text-muted-foreground size-4" />
                                    <span className="font-mono text-sm font-medium">
                                      {name}
                                    </span>
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      {sig.input_fields.length} →{" "}
                                      {sig.output_fields.length}
                                    </Badge>
                                  </div>
                                  {expandedSignatures.has(name) ? (
                                    <ChevronUp className="text-muted-foreground size-4" />
                                  ) : (
                                    <ChevronDown className="text-muted-foreground size-4" />
                                  )}
                                </button>
                                <AnimatePresence>
                                  {expandedSignatures.has(name) && (
                                    <motion.div
                                      initial={{ height: 0, opacity: 0 }}
                                      animate={{ height: "auto", opacity: 1 }}
                                      exit={{ height: 0, opacity: 0 }}
                                      transition={{ duration: 0.2 }}
                                      className="overflow-hidden"
                                    >
                                      <div className="bg-muted/30 border-t p-3">
                                        {sig.instructions && (
                                          <p className="text-muted-foreground mb-3 text-sm">
                                            {sig.instructions}
                                          </p>
                                        )}
                                        <div className="grid gap-3 md:grid-cols-2">
                                          <div>
                                            <h5 className="mb-1 text-xs font-medium uppercase tracking-wider opacity-70">
                                              Inputs
                                            </h5>
                                            <div className="flex flex-wrap gap-1">
                                              {sig.input_fields.map((field) => (
                                                <Badge
                                                  key={field}
                                                  variant="secondary"
                                                  className="font-mono text-xs"
                                                >
                                                  {field}
                                                </Badge>
                                              ))}
                                              {sig.input_fields.length ===
                                                0 && (
                                                <span className="text-muted-foreground text-xs">
                                                  None
                                                </span>
                                              )}
                                            </div>
                                          </div>
                                          <div>
                                            <h5 className="mb-1 text-xs font-medium uppercase tracking-wider opacity-70">
                                              Outputs
                                            </h5>
                                            <div className="flex flex-wrap gap-1">
                                              {sig.output_fields.map(
                                                (field) => (
                                                  <Badge
                                                    key={field}
                                                    variant="default"
                                                    className="font-mono text-xs"
                                                  >
                                                    {field}
                                                  </Badge>
                                                ),
                                              )}
                                              {sig.output_fields.length ===
                                                0 && (
                                                <span className="text-muted-foreground text-xs">
                                                  None
                                                </span>
                                              )}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            ),
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history">
              <motion.div variants={itemVariants}>
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          <History className="size-5" />
                          Execution History
                        </CardTitle>
                        <CardDescription>
                          Recent workflow executions with quality metrics
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() =>
                            setHistoryOffset((v) =>
                              Math.max(0, v - historyLimit),
                            )
                          }
                          disabled={
                            historyOffset === 0 || historyQuery.isFetching
                          }
                        >
                          <ChevronLeft className="size-4" />
                        </Button>
                        <span className="text-muted-foreground min-w-[3ch] text-center font-mono text-xs">
                          {Math.floor(historyOffset / historyLimit) + 1}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() =>
                            setHistoryOffset((v) => v + historyLimit)
                          }
                          disabled={
                            historyQuery.isFetching ||
                            (historyQuery.data?.length ?? 0) < historyLimit
                          }
                        >
                          <ChevronRight className="size-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {historyQuery.isLoading ? (
                      <div className="text-muted-foreground flex items-center justify-center py-8">
                        <Loader2 className="mr-2 size-4 animate-spin" />
                        Loading history...
                      </div>
                    ) : historyQuery.isError ? (
                      <div className="flex items-center justify-center py-8 text-red-500">
                        <XCircle className="mr-2 size-4" />
                        Failed to load history
                      </div>
                    ) : historyQuery.data?.length ? (
                      <div className="divide-border -mx-3 divide-y">
                        {historyQuery.data.map((entry, index) => (
                          <HistoryEntry
                            key={
                              entry.workflowId ??
                              entry.workflow_id ??
                              `entry-${index}`
                            }
                            entry={entry}
                            index={index}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="text-muted-foreground flex flex-col items-center justify-center py-8 text-sm">
                        <Database className="mb-2 size-8 opacity-30" />
                        <p>No history entries found</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}
