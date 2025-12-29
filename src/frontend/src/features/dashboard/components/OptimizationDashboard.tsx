// import { useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TextShimmer } from "@/features/chat";
import { useOptimizationDashboard } from "@/features/dashboard/hooks/useOptimizationDashboard";
import { OptimizationControls } from "./OptimizationControls";
// import { cn } from "@/lib/utils";
import { ChatHeader } from "@/features/layout";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Activity,
  Zap,
  Database,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  BarChart3,
  History as HistoryIcon,
  ChevronLeft,
  ChevronRight,
  Settings2,
  Target,
  FileCode,
  Hash,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  BrainCircuit,
  Trash2,
  HardDrive,
} from "lucide-react";

import {
  StatusBadge,
  StatCard,
  ProgressRing,
  HistoryEntry,
  QualityChart,
} from "./shared";

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

// ============================================================================
// Main Optimization Dashboard Component
// ============================================================================

export function OptimizationDashboard() {
  // Use the centralized hook for all state management
  const {
    // State
    jobId,
    setJobId,
    historyOffset,
    setHistoryOffset,
    historyLimit,
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
  } = useOptimizationDashboard();

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="flex h-full w-full flex-col">
      {/* Header */}
      <ChatHeader
        title="Optimization Control"
        sidebarTrigger={<SidebarTrigger />}
        className="bg-transparent sticky top-0 z-10"
        actions={<StatusBadge status={currentStatus} />}
      />

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
                  {optimizationStatus.data?.progress_message && (
                    <p className="text-muted-foreground mt-2 text-xs">
                      {optimizationStatus.data.progress_message}
                    </p>
                  )}
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
                  selfImproveStats?.average_quality_score !== undefined &&
                  selfImproveStats.average_quality_score > 0
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
                <HistoryIcon className="mr-1.5 size-4" />
                History
              </TabsTrigger>
            </TabsList>

            {/* Optimize Tab */}
            <TabsContent value="optimize">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Configuration */}
                <OptimizationControls
                  optimizer={optimizer}
                  setOptimizer={setOptimizer}
                  gepaPreset={gepaPreset}
                  setGepaPreset={setGepaPreset}
                  minQuality={minQuality}
                  setMinQuality={setMinQuality}
                  maxIterations={maxIterations}
                  setMaxIterations={setMaxIterations}
                  harvestHistory={harvestHistory}
                  setHarvestHistory={setHarvestHistory}
                  historyHarvestLimit={historyHarvestLimit}
                  setHistoryHarvestLimit={setHistoryHarvestLimit}
                  minQualityError={minQualityError}
                  setMinQualityError={setMinQualityError}
                  maxIterationsError={maxIterationsError}
                  setMaxIterationsError={setMaxIterationsError}
                  isOptimizing={isOptimizing}
                  optimizationRun={optimizationRun}
                  handleStartOptimization={handleStartOptimization}
                />

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
                            {optimizationStatus.data?.progress_current !==
                              undefined &&
                              optimizationStatus.data?.progress_total !==
                                undefined && (
                                <span className="text-muted-foreground ml-1">
                                  ({optimizationStatus.data.progress_current}/
                                  {optimizationStatus.data.progress_total})
                                </span>
                              )}
                          </span>
                        </div>
                        <Progress value={currentProgress} className="h-2" />
                        <p className="text-muted-foreground text-xs">
                          {currentMessage}
                        </p>
                        {optimizationStatus.data?.progress_duration && (
                          <p className="text-muted-foreground mt-1 text-xs">
                            Duration:{" "}
                            {Math.round(
                              optimizationStatus.data.progress_duration,
                            )}
                            s
                          </p>
                        )}
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
                            onChange={(e) => {
                              setMinQuality(e.target.value);
                              setMinQualityError(null); // Clear error on change
                            }}
                            disabled={selfImprove.isPending}
                            placeholder="8.0"
                            className={minQualityError ? "border-red-500" : ""}
                          />
                          {minQualityError && (
                            <p className="mt-1 text-xs text-red-500">
                              {minQualityError}
                            </p>
                          )}
                        </div>
                        <div>
                          <label className="text-muted-foreground mb-2 block text-sm font-medium">
                            Max Examples
                          </label>
                          <Input
                            inputMode="numeric"
                            value={maxExamples}
                            onChange={(e) => {
                              setMaxExamples(e.target.value);
                              setMaxExamplesError(null); // Clear error on change
                            }}
                            disabled={selfImprove.isPending}
                            placeholder="20"
                            className={maxExamplesError ? "border-red-500" : ""}
                          />
                          {maxExamplesError && (
                            <p className="mt-1 text-xs text-red-500">
                              {maxExamplesError}
                            </p>
                          )}
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
                        {optimizationRun.isSuccess && (
                          <motion.div
                            key="result"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-primary/10 border-primary/20 text-primary flex items-start gap-2 rounded-lg border p-3 text-sm"
                          >
                            <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                            <span>
                              Self-improvement job started! Job ID: {jobId}
                            </span>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {selfImprove.isError && (
                        <div className="bg-destructive/10 border-destructive/20 text-destructive flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
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
                            <div className="text-destructive flex items-center gap-2 text-sm">
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
                            <div className="text-destructive flex items-center gap-2 text-sm">
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
                        <div className="bg-primary/10 border-primary/20 text-primary flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
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
                        <div className="text-destructive flex items-center justify-center py-8">
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
                            <div className="text-primary flex items-center gap-2">
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
                            <div className="bg-primary/10 border-primary/20 text-primary flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
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
                        <div className="text-destructive flex items-center justify-center py-8">
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
                          <HistoryIcon className="size-5" />
                          Execution History
                        </CardTitle>
                        <CardDescription>
                          Recent workflow executions with quality metrics
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="size-8 p-0"
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
                          size="sm"
                          className="size-8 p-0"
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
                      <div className="text-destructive flex items-center justify-center py-8">
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
