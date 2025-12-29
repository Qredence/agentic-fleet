/**
 * Shared components for Optimization Dashboard.
 *
 * Reusable UI components used across dashboard tabs.
 */

import { useMemo } from "react";
import { motion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { HistoryExecutionEntry } from "@/api/types";

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
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

export function StatCard({ label, value, icon, description }: StatCardProps) {
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
        <div className="from-primary/5 pointer-events-none absolute inset-0 bg-linear-to-br to-transparent" />
      </Card>
    </motion.div>
  );
}

// ============================================================================
// Progress Ring Component (SVG-based)
// ============================================================================

interface ProgressRingProps {
  progress: number;
  status: string; // broadened from literal union to string
}

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

export function ProgressRing({ progress, status }: ProgressRingProps) {
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  const statusColors = useMemo(
    () => ({
      idle: { stroke: "stroke-muted", fill: "text-muted-foreground" },
      running: { stroke: "stroke-primary", fill: "text-primary" },
      completed: { stroke: "stroke-primary", fill: "text-primary" },
      failed: { stroke: "stroke-destructive", fill: "text-destructive" },
    }),
    [],
  );

  const { stroke, fill } =
    statusColors[status as keyof typeof statusColors] || statusColors.idle;

  return (
    <motion.div
      className="relative"
      variants={pulseVariants}
      animate={status === "running" ? "active" : "idle"}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted/30"
        />
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

export function QualityChart({ distribution }: QualityChartProps) {
  const entries = Object.entries(distribution);
  const maxValue = Math.max(...entries.map(([, v]) => v), 1);

  const barColors = [
    "bg-primary",
    "bg-secondary",
    "bg-muted-foreground",
    "bg-destructive",
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

export function HistoryEntry({ entry, index }: HistoryEntryProps) {
  const workflowId = entry.workflowId ?? entry.workflow_id ?? "unknown";
  const task = typeof entry.task === "string" ? entry.task : "(no task)";
  const qualityScore =
    entry.quality_score ?? entry.qualityScore ?? entry.quality?.score;
  const qualityFlag =
    entry.quality_flag ?? entry.qualityFlag ?? entry.quality?.flag;

  const scoreColor = useMemo(() => {
    if (qualityScore === undefined || qualityScore === null)
      return "text-muted-foreground";
    // Ensure we are comparing numbers
    const score = Number(qualityScore);
    if (isNaN(score)) return "text-muted-foreground";

    if (score >= 8) return "text-primary";
    if (score >= 6) return "text-yellow-500";
    return "text-destructive";
  }, [qualityScore]);

  return (
    <div className="hover:bg-muted/50 p-3 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground font-mono text-xs">
              #{index + 1}
            </span>
            <StatusBadge
              status={
                typeof entry.status === "string" ? entry.status : "unknown"
              }
            />
            {qualityFlag && (
              <Badge variant="outline" className="text-xs">
                {String(qualityFlag)}
              </Badge>
            )}
          </div>
          <p className="text-foreground line-clamp-2 text-sm">{task}</p>
          <div className="text-muted-foreground flex items-center gap-4 text-xs">
            <span className="font-mono">{workflowId.slice(0, 12)}...</span>
            {entry.created_at && (
              <span>{new Date(entry.created_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        {qualityScore !== undefined && (
          <div className="flex flex-col items-end gap-1">
            <span className={cn("font-mono text-lg font-bold", scoreColor)}>
              {typeof qualityScore === "number"
                ? qualityScore.toFixed(1)
                : String(qualityScore)}
            </span>
            <span className="text-muted-foreground text-xs">Quality</span>
          </div>
        )}
      </div>
    </div>
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

export function OptimizerSelector({
  value,
  onChange,
  disabled,
}: OptimizerSelectorProps) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <button
        type="button"
        onClick={() => onChange("bootstrap")}
        disabled={disabled}
        className={cn(
          "rounded-lg border p-3 text-left transition-colors",
          value === "bootstrap"
            ? "border-primary bg-primary/10"
            : "border-border hover:bg-muted/50",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      >
        <div className="font-medium">Bootstrap</div>
        <div className="text-muted-foreground text-xs">
          Fast, minimal examples
        </div>
      </button>
      <button
        type="button"
        onClick={() => onChange("gepa")}
        disabled={disabled}
        className={cn(
          "rounded-lg border p-3 text-left transition-colors",
          value === "gepa"
            ? "border-primary bg-primary/10"
            : "border-border hover:bg-muted/50",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      >
        <div className="font-medium">GEPA</div>
        <div className="text-muted-foreground text-xs">
          Advanced optimization
        </div>
      </button>
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

export function GepaPresetSelector({
  value,
  onChange,
  disabled,
}: GepaPresetSelectorProps) {
  const presets = [
    { value: "light" as const, label: "Light", desc: "Fast, ~5 calls" },
    { value: "medium" as const, label: "Medium", desc: "Balanced, ~10 calls" },
    { value: "heavy" as const, label: "Heavy", desc: "Thorough, ~20 calls" },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {presets.map((preset) => (
        <button
          key={preset.value}
          type="button"
          onClick={() => onChange(preset.value)}
          disabled={disabled}
          className={cn(
            "rounded-lg border p-2 text-center transition-colors",
            value === preset.value
              ? "border-primary bg-primary/10"
              : "border-border hover:bg-muted/50",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <div className="font-medium text-sm">{preset.label}</div>
          <div className="text-muted-foreground text-xs">{preset.desc}</div>
        </button>
      ))}
    </div>
  );
}
