import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronRight,
  ChevronDown,
  Clock,
  Database,
  Activity,
  AlertCircle,
  ExternalLink,
  Code2,
  Brain,
} from "lucide-react";
import { observabilityApi } from "@/api/client";
import type { TraceDetails, Observation } from "@/api/types";
import { formatDistanceToNow } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// Removed local Observation interface in favor of global one from @/api/types

interface TraceExplorerProps {
  workflowId: string;
  onClose?: () => void;
}

/**
 * ObservationItem - Renders a single span or event in the trace hierarchy
 */
const ObservationItem: React.FC<{
  observation: Observation;
  children?: React.ReactNode;
  level: number;
}> = ({ observation, children, level }) => {
  const [isOpen, setIsOpen] = useState(level < 2); // Open top levels by default
  const hasChildren = React.Children.count(children) > 0;

  const duration = observation.endTime
    ? new Date(observation.endTime).getTime() -
      new Date(observation.startTime).getTime()
    : null;

  return (
    <div className="flex flex-col">
      <div
        className={cn(
          "flex items-center group py-2 px-3 hover:bg-muted/50 rounded-lg cursor-pointer transition-colors",
          level > 0 && "ml-4 border-l border-border/50 pl-4",
        )}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {hasChildren ? (
            isOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          ) : (
            <div className="w-4" />
          )}

          <div className="flex items-center gap-2 min-w-0">
            {observation.name.toLowerCase().includes("reasoner") ||
            observation.metadata?.module_name ? (
              <Brain className="h-4 w-4 text-purple-500 shrink-0" />
            ) : observation.name.toLowerCase().includes("agent") ? (
              <Activity className="h-4 w-4 text-blue-500 shrink-0" />
            ) : (
              <Code2 className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
            <span className="font-medium truncate">{observation.name}</span>
          </div>

          {!!observation.metadata?.module_name && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 h-4 uppercase tracking-wider text-muted-foreground"
            >
              {String(observation.metadata.module_name)}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
          {duration !== null && (
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {duration}ms
            </div>
          )}
          {observation.model && (
            <div className="flex items-center gap-1 bg-muted px-2 py-0.5 rounded text-[10px] font-mono">
              {observation.model}
            </div>
          )}
        </div>
      </div>

      {isOpen && hasChildren && <div className="flex flex-col">{children}</div>}

      {isOpen &&
        !hasChildren &&
        (!!observation.input || !!observation.output) && (
          <div
            className={cn(
              "mt-1 p-3 bg-muted/30 rounded-lg text-xs font-mono space-y-2 overflow-x-auto",
              level > 0 && "ml-8",
            )}
          >
            {!!observation.input && (
              <div>
                <div className="text-muted-foreground mb-1 uppercase text-[10px] font-bold tracking-tighter">
                  Input:
                </div>
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(observation.input, null, 2)}
                </pre>
              </div>
            )}
            {!!observation.output && (
              <div>
                <div className="text-muted-foreground mb-1 uppercase text-[10px] font-bold tracking-tighter">
                  Output:
                </div>
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(observation.output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
    </div>
  );
};

/**
 * TraceExplorer - Main component for exploring workflow traces
 */
export const TraceExplorer: React.FC<TraceExplorerProps> = ({
  workflowId,
  onClose,
}) => {
  const { data, isLoading, error } = useQuery<TraceDetails>({
    queryKey: ["trace", workflowId],
    queryFn: () => observabilityApi.getTrace(workflowId),
    retry: 1,
  });

  if (isLoading) {
    return (
      <Card className="w-full h-full border-none shadow-none bg-transparent">
        <CardHeader>
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center space-y-4">
        <AlertCircle className="h-12 w-12 text-destructive opacity-50" />
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground">
            Trace unavailable
          </h3>
          <p className="text-sm text-muted-foreground max-w-xs mx-auto">
            {error instanceof Error
              ? error.message
              : "We couldn't find the trace for this execution. It might still be processing or Langfuse is disconnected."}
          </p>
        </div>
        <Button variant="outline" onClick={onClose} size="sm">
          Close Explorer
        </Button>
      </div>
    );
  }

  // Organize observations into a tree structure
  const buildTree = (observations: Observation[]) => {
    const map = new Map<string, { obs: Observation; children: any[] }>();
    const roots: any[] = [];

    // Sort by start time to ensure correct ordering
    const sorted = [...observations].sort(
      (a, b) =>
        new Date(a.startTime).getTime() - new Date(b.startTime).getTime(),
    );

    sorted.forEach((o) => {
      map.set(o.id, { obs: o, children: [] });
    });

    sorted.forEach((o) => {
      if (o.parentObservationId && map.has(o.parentObservationId)) {
        map.get(o.parentObservationId)!.children.push(map.get(o.id));
      } else {
        roots.push(map.get(o.id));
      }
    });

    return roots;
  };

  const renderTree = (node: any, level: number = 0) => {
    return (
      <ObservationItem key={node.obs.id} observation={node.obs} level={level}>
        {node.children.map((child: any) => renderTree(child, level + 1))}
      </ObservationItem>
    );
  };

  const tree = buildTree(data.observations || []);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b flex items-center justify-between shrink-0">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold font-mono tracking-tight">
              {data.name || "Workflow Execution"}
            </h2>
            <Badge variant="secondary" className="font-mono text-[10px]">
              {workflowId.slice(0, 8)}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Started{" "}
            {formatDistanceToNow(new Date(data.timestamp), { addSuffix: true })}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `https://cloud.langfuse.com/trace/${workflowId}`,
                "_blank",
              )
            }
          >
            <ExternalLink className="h-3.5 w-3.5 mr-2" />
            Langfuse Cloud
          </Button>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Quality Scores */}
        {data.scores && data.scores.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.scores.map((score, i) => (
              <Card
                key={i}
                className="bg-primary/5 border-primary/20 shadow-none"
              >
                <CardContent className="pt-4 flex items-start gap-4">
                  <div className="h-12 w-12 rounded-full border-4 border-primary/30 flex items-center justify-center text-primary shrink-0">
                    <span className="text-lg font-bold">
                      {(score.value * 100).toFixed(0)}
                    </span>
                  </div>
                  <div className="space-y-1 min-w-0">
                    <div className="text-xs font-bold uppercase tracking-wider text-primary/70">
                      {score.name}
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2 italic">
                      {score.comment || "Automated LLM quality assessment"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Execution Hierarchy */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
            <Activity className="h-4 w-4" />
            Execution Flow
          </div>
          <div className="bg-card/30 rounded-xl border p-4 space-y-1">
            {tree.length > 0 ? (
              tree.map((root) => renderTree(root))
            ) : (
              <div className="py-12 text-center text-muted-foreground text-sm flex flex-col items-center gap-3">
                <Database className="h-8 w-8 opacity-20" />
                No execution details found for this trace.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
