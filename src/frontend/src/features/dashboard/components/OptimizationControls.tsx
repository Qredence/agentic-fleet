/**
 * Optimization Controls Component
 *
 * Handles input controls and validation for the optimization tab.
 */

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
import { OptimizerSelector, GepaPresetSelector } from "./shared";
import { Settings2, Play, RefreshCw, Loader2, XCircle } from "lucide-react";

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

interface OptimizationControlsProps {
  optimizer: "bootstrap" | "gepa";
  setOptimizer: (value: "bootstrap" | "gepa") => void;
  gepaPreset: "light" | "medium" | "heavy";
  setGepaPreset: (value: "light" | "medium" | "heavy") => void;
  minQuality: string;
  setMinQuality: (value: string) => void;
  maxIterations: string;
  setMaxIterations: (value: string) => void;
  harvestHistory: boolean;
  setHarvestHistory: (value: boolean) => void;
  historyHarvestLimit: string;
  setHistoryHarvestLimit: (value: string) => void;
  minQualityError: string | null;
  setMinQualityError: (value: string | null) => void;
  maxIterationsError: string | null;
  setMaxIterationsError: (value: string | null) => void;
  isOptimizing: boolean;
  optimizationRun: {
    isPending: boolean;
    isError: boolean;
  };
  handleStartOptimization: () => void;
}

export function OptimizationControls({
  optimizer,
  setOptimizer,
  gepaPreset,
  setGepaPreset,
  minQuality,
  setMinQuality,
  maxIterations,
  setMaxIterations,
  harvestHistory,
  setHarvestHistory,
  historyHarvestLimit,
  setHistoryHarvestLimit,
  minQualityError,
  setMinQualityError,
  maxIterationsError,
  setMaxIterationsError,
  isOptimizing,
  optimizationRun,
  handleStartOptimization,
}: OptimizationControlsProps) {
  return (
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

          {/* Min Quality + Max Iterations */}
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
                  setMinQualityError(null);
                }}
                disabled={isOptimizing}
                placeholder="8.0"
                className={minQualityError ? "border-red-500" : ""}
              />
              {minQualityError && (
                <p className="mt-1 text-xs text-red-500">{minQualityError}</p>
              )}
            </div>
            {optimizer === "gepa" && (
              <div>
                <label className="text-muted-foreground mb-2 block text-sm font-medium">
                  Max Iterations
                </label>
                <Input
                  inputMode="numeric"
                  value={maxIterations}
                  onChange={(e) => {
                    setMaxIterations(e.target.value);
                    setMaxIterationsError(null);
                  }}
                  disabled={isOptimizing}
                  placeholder="10"
                  className={maxIterationsError ? "border-red-500" : ""}
                />
                {maxIterationsError && (
                  <p className="mt-1 text-xs text-red-500">
                    {maxIterationsError}
                  </p>
                )}
                <p className="text-muted-foreground mt-1 text-xs">
                  Limit GEPA generations (optional)
                </p>
              </div>
            )}
          </div>

          {/* Harvest History */}
          <AnimatePresence mode="wait">
            {harvestHistory && (
              <motion.div
                key="history-config"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-3"
              >
                <div>
                  <label className="text-muted-foreground mb-2 block text-sm font-medium">
                    History Limit
                  </label>
                  <Input
                    inputMode="numeric"
                    value={historyHarvestLimit}
                    onChange={(e) => setHistoryHarvestLimit(e.target.value)}
                    disabled={isOptimizing}
                    placeholder="200"
                  />
                  <p className="text-muted-foreground mt-1 text-xs">
                    Maximum number of history entries to harvest
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div>
            <label className="text-muted-foreground mb-2 block text-sm font-medium">
              Use Execution History
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
            <p className="text-muted-foreground mt-1 text-xs">
              Use high-quality execution history as training data
            </p>
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
            <div className="bg-destructive/10 border-destructive/20 text-destructive flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
              <XCircle className="size-4" />
              Failed to start optimization
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
