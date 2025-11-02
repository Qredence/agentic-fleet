import React, { useState, useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { performanceMonitor, usePerformanceMonitor } from "@/utils/performance";
import { chatApi } from "@/api/chatApi";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

// Types
interface StreamingDashboardProps {
  className?: string;
  conversationId?: string;
  showRealTimeMetrics?: boolean;
  enableAlerts?: boolean;
  alertThresholds?: {
    responseTime: number; // ms
    chunkDelay: number; // ms
    errorRate: number; // percentage
  };
}

interface RealTimeMetrics {
  timestamp: number;
  activeStreams: number;
  totalRequests: number;
  averageResponseTime: number;
  streamingLatency: number;
  errorRate: number;
  bandwidthUsage: number;
  memoryUsage: number;
}

interface StreamMetrics {
  messageId: string;
  agentName: string;
  startTime: number;
  currentContent: string;
  chunksReceived: number;
  totalChunks: number;
  averageChunkDelay: number;
  estimatedCompletion: number;
  isPaused: boolean;
  errors: number;
}

interface ConnectionQuality {
  type: string;
  rtt: number;
  downlink: number;
  effectiveType: string;
  saveData: boolean;
}

// Icons
const ActivityIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M22 12h-4l-3 9L9 3l-3 9H2"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const WarningIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <line
      x1="12"
      y1="9"
      x2="12"
      y2="13"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <line
      x1="12"
      y1="17"
      x2="12.01"
      y2="17"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CheckCircleIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M22 11.08V12a10 10 0 1 1-5.93-9.14"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <polyline
      points="22 4 12 14.01 9 11.01"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const XCircleIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
    <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" strokeWidth="2" />
    <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const NetworkIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M5 12.55a11 11 0 0 1 14.08 0"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M1.42 9a16 16 0 0 1 21.16 0"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M8.53 16.11a6 6 0 0 1 6.95 0"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <line
      x1="12"
      y1="20"
      x2="12.01"
      y2="20"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// Streaming Dashboard Component
export const StreamingDashboard: React.FC<StreamingDashboardProps> = React.memo(
  ({
    className,
    conversationId,
    showRealTimeMetrics = true,
    enableAlerts = true,
    alertThresholds = {
      responseTime: 5000, // 5 seconds
      chunkDelay: 1000, // 1 second
      errorRate: 10, // 10%
    },
  }) => {
    const { currentConversationId, streaming, performanceMetrics } =
      useChatStore();
    const perf = usePerformanceMonitor();

    const activeConversationId = conversationId || currentConversationId;

    // Local state
    const [realTimeMetrics, setRealTimeMetrics] = useState<RealTimeMetrics>({
      timestamp: Date.now(),
      activeStreams: 0,
      totalRequests: 0,
      averageResponseTime: 0,
      streamingLatency: 0,
      errorRate: 0,
      bandwidthUsage: 0,
      memoryUsage: 0,
    });

    const [activeStreams, setActiveStreams] = useState<StreamMetrics[]>([]);
    const [connectionQuality, setConnectionQuality] =
      useState<ConnectionQuality | null>(null);
    const [alerts, setAlerts] = useState<
      Array<{
        id: string;
        type: "warning" | "error" | "success";
        message: string;
        timestamp: number;
      }>
    >([]);

    const [showDetails, setShowDetails] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(true);

    // Refs
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const alertTimeoutRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

    // Get connection quality
    useEffect(() => {
      if ("connection" in navigator) {
        const conn = (navigator as any).connection;
        setConnectionQuality({
          type: conn.type || "unknown",
          rtt: conn.rtt || 0,
          downlink: conn.downlink || 0,
          effectiveType: conn.effectiveType || "unknown",
          saveData: conn.saveData || false,
        });

        const handleConnectionChange = () => {
          setConnectionQuality({
            type: conn.type || "unknown",
            rtt: conn.rtt || 0,
            downlink: conn.downlink || 0,
            effectiveType: conn.effectiveType || "unknown",
            saveData: conn.saveData || false,
          });
        };

        conn.addEventListener("change", handleConnectionChange);
        return () => conn.removeEventListener("change", handleConnectionChange);
      }
    }, []);

    // Update real-time metrics
    useEffect(() => {
      if (!showRealTimeMetrics || !autoRefresh) return;

      const updateMetrics = () => {
        const summary = perf.getPerformanceSummary();
        const now = Date.now();

        // Get memory usage if available
        let memoryUsage = 0;
        if ("memory" in performance) {
          const memory = (performance as any).memory;
          memoryUsage = memory.usedJSHeapSize / 1024 / 1024; // MB
        }

        // Calculate active streams
        const activeStreamsCount = streaming.isStreaming ? 1 : 0;

        const newMetrics: RealTimeMetrics = {
          timestamp: now,
          activeStreams: activeStreamsCount,
          totalRequests: summary.totalStreams,
          averageResponseTime: summary.averageDuration,
          streamingLatency:
            summary.averageChunks > 0
              ? summary.averageDuration / summary.averageChunks
              : 0,
          errorRate: summary.errorRate * 100,
          bandwidthUsage: 0, // Would need to implement actual bandwidth tracking
          memoryUsage,
        };

        setRealTimeMetrics(newMetrics);

        // Update active streams
        if (streaming.isStreaming && streaming.currentMessageId) {
          const streamMetrics: StreamMetrics = {
            messageId: streaming.currentMessageId,
            agentName: streaming.agentName || "Assistant",
            startTime: streaming.startTime || now,
            currentContent: "", // Would need to track this
            chunksReceived: streaming.chunkCount,
            totalChunks: 50, // Estimated
            averageChunkDelay: streaming.estimatedCompletion
              ? (streaming.estimatedCompletion - streaming.startTime) /
                streaming.chunkCount
              : 0,
            estimatedCompletion: streaming.estimatedCompletion || 0,
            isPaused: !streaming.isStreaming,
            errors: 0, // Would need to track this
          };

          setActiveStreams([streamMetrics]);
        } else {
          setActiveStreams([]);
        }

        // Check for alerts
        if (enableAlerts) {
          checkForAlerts(newMetrics);
        }
      };

      updateMetrics();
      intervalRef.current = setInterval(updateMetrics, 1000);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }, [showRealTimeMetrics, autoRefresh, streaming, perf, enableAlerts]);

    // Alert checking
    const checkForAlerts = (metrics: RealTimeMetrics) => {
      const newAlerts: Array<{
        id: string;
        type: "warning" | "error" | "success";
        message: string;
        timestamp: number;
      }> = [];

      // Response time alert
      if (metrics.averageResponseTime > alertThresholds.responseTime) {
        const alertId = "response-time";
        newAlerts.push({
          id: alertId,
          type: "warning",
          message: `High response time: ${metrics.averageResponseTime.toFixed(0)}ms`,
          timestamp: Date.now(),
        });
        scheduleAlertRemoval(alertId, 10000);
      }

      // Chunk delay alert
      if (metrics.streamingLatency > alertThresholds.chunkDelay) {
        const alertId = "chunk-delay";
        newAlerts.push({
          id: alertId,
          type: "warning",
          message: `Slow streaming: ${metrics.streamingLatency.toFixed(0)}ms average delay`,
          timestamp: Date.now(),
        });
        scheduleAlertRemoval(alertId, 8000);
      }

      // Error rate alert
      if (metrics.errorRate > alertThresholds.errorRate) {
        const alertId = "error-rate";
        newAlerts.push({
          id: alertId,
          type: "error",
          message: `High error rate: ${metrics.errorRate.toFixed(1)}%`,
          timestamp: Date.now(),
        });
        scheduleAlertRemoval(alertId, 15000);
      }

      // Memory usage alert
      if (metrics.memoryUsage > 100) {
        // 100MB
        const alertId = "memory-usage";
        newAlerts.push({
          id: alertId,
          type: "warning",
          message: `High memory usage: ${metrics.memoryUsage.toFixed(1)}MB`,
          timestamp: Date.now(),
        });
        scheduleAlertRemoval(alertId, 12000);
      }

      // Connection quality alert
      if (connectionQuality && connectionQuality.effectiveType === "slow-2g") {
        const alertId = "connection-quality";
        newAlerts.push({
          id: alertId,
          type: "warning",
          message: "Slow connection detected",
          timestamp: Date.now(),
        });
        scheduleAlertRemoval(alertId, 20000);
      }

      if (newAlerts.length > 0) {
        setAlerts((prev) => [...prev, ...newAlerts].slice(-10)); // Keep last 10 alerts
      }
    };

    const scheduleAlertRemoval = (alertId: string, delay: number) => {
      // Clear existing timeout
      const existingTimeout = alertTimeoutRef.current.get(alertId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      // Schedule removal
      const timeout = setTimeout(() => {
        setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
        alertTimeoutRef.current.delete(alertId);
      }, delay);

      alertTimeoutRef.current.set(alertId, timeout);
    };

    // Format bytes
    const formatBytes = (bytes: number) => {
      if (bytes === 0) return "0 B";
      const k = 1024;
      const sizes = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    };

    // Get connection quality indicator
    const getConnectionQualityColor = (quality: ConnectionQuality | null) => {
      if (!quality) return "text-gray-500";

      switch (quality.effectiveType) {
        case "slow-2g":
        case "2g":
          return "text-red-500";
        case "3g":
          return "text-yellow-500";
        case "4g":
          return "text-green-500";
        default:
          return "text-gray-500";
      }
    };

    // Get performance rating
    const getPerformanceRating = (metrics: RealTimeMetrics) => {
      let score = 100;

      // Response time impact (40% weight)
      if (metrics.averageResponseTime > 10000) score -= 40;
      else if (metrics.averageResponseTime > 5000) score -= 30;
      else if (metrics.averageResponseTime > 2000) score -= 20;
      else if (metrics.averageResponseTime > 1000) score -= 10;

      // Error rate impact (30% weight)
      score -= metrics.errorRate * 3;

      // Streaming latency impact (20% weight)
      if (metrics.streamingLatency > 2000) score -= 20;
      else if (metrics.streamingLatency > 1000) score -= 15;
      else if (metrics.streamingLatency > 500) score -= 10;
      else if (metrics.streamingLatency > 200) score -= 5;

      // Memory usage impact (10% weight)
      if (metrics.memoryUsage > 200) score -= 10;
      else if (metrics.memoryUsage > 100) score -= 5;

      if (score >= 90)
        return {
          rating: "Excellent",
          color: "text-green-600",
          icon: CheckCircleIcon,
        };
      if (score >= 75)
        return {
          rating: "Good",
          color: "text-blue-600",
          icon: CheckCircleIcon,
        };
      if (score >= 60)
        return { rating: "Fair", color: "text-yellow-600", icon: WarningIcon };
      return { rating: "Poor", color: "text-red-600", icon: XCircleIcon };
    };

    const performanceRating = getPerformanceRating(realTimeMetrics);
    const RatingIcon = performanceRating.icon;

    return (
      <div className={cn("space-y-4", className)}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ActivityIcon className="w-5 h-5" />
            <h3 className="text-lg font-semibold">Streaming Performance</h3>
            <Badge variant="outline" className="text-xs">
              {realTimeMetrics.activeStreams} active
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 text-sm">
              <Label htmlFor="auto-refresh">Auto-refresh</Label>
              <Switch
                id="auto-refresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? "Hide Details" : "Show Details"}
            </Button>
          </div>
        </div>

        {/* Alerts */}
        {enableAlerts && alerts.length > 0 && (
          <div className="space-y-2">
            {alerts.slice(-3).map((alert) => (
              <Alert
                key={alert.id}
                variant={alert.type === "error" ? "destructive" : "default"}
              >
                <div className="flex items-center gap-2">
                  {alert.type === "error" && (
                    <XCircleIcon className="w-4 h-4" />
                  )}
                  {alert.type === "warning" && (
                    <WarningIcon className="w-4 h-4" />
                  )}
                  {alert.type === "success" && (
                    <CheckCircleIcon className="w-4 h-4" />
                  )}
                  <AlertDescription>{alert.message}</AlertDescription>
                </div>
              </Alert>
            ))}
          </div>
        )}

        {/* Main metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Response Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {realTimeMetrics.averageResponseTime.toFixed(0)}ms
              </div>
              <div className="text-xs text-muted-foreground">
                Average over last {realTimeMetrics.totalRequests} requests
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Streaming Latency
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {realTimeMetrics.streamingLatency.toFixed(0)}ms
              </div>
              <div className="text-xs text-muted-foreground">
                Average chunk delay
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {realTimeMetrics.errorRate.toFixed(1)}%
              </div>
              <div className="text-xs text-muted-foreground">
                {realTimeMetrics.totalRequests > 0
                  ? `${Math.round((realTimeMetrics.totalRequests * realTimeMetrics.errorRate) / 100)} errors`
                  : "No errors"}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Performance Rating
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <RatingIcon
                  className={cn("w-5 h-5", performanceRating.color)}
                />
                <span
                  className={cn("text-lg font-bold", performanceRating.color)}
                >
                  {performanceRating.rating}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                Overall system health
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Detailed metrics */}
        {showDetails && (
          <Tabs defaultValue="streams" className="space-y-4">
            <TabsList>
              <TabsTrigger value="streams">Active Streams</TabsTrigger>
              <TabsTrigger value="system">System Metrics</TabsTrigger>
              <TabsTrigger value="network">Network Quality</TabsTrigger>
              <TabsTrigger value="history">Performance History</TabsTrigger>
            </TabsList>

            <TabsContent value="streams" className="space-y-4">
              {activeStreams.length > 0 ? (
                activeStreams.map((stream) => (
                  <Card key={stream.messageId}>
                    <CardHeader>
                      <CardTitle className="text-sm">
                        {stream.agentName}
                      </CardTitle>
                      <CardDescription>
                        Message ID: {stream.messageId}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">
                            Progress:
                          </span>
                          <div className="flex items-center gap-2 mt-1">
                            <Progress
                              value={
                                (stream.chunksReceived / stream.totalChunks) *
                                100
                              }
                              className="flex-1"
                            />
                            <span>
                              {stream.chunksReceived}/{stream.totalChunks}
                            </span>
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Status:</span>
                          <Badge
                            variant={stream.isPaused ? "secondary" : "default"}
                            className="ml-2"
                          >
                            {stream.isPaused ? "Paused" : "Active"}
                          </Badge>
                        </div>
                        <div>
                          <span className="text-muted-foreground">
                            Chunk Delay:
                          </span>
                          <div className="font-mono mt-1">
                            {stream.averageChunkDelay.toFixed(0)}ms
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">ETA:</span>
                          <div className="font-mono mt-1">
                            {stream.estimatedCompletion > 0
                              ? `${Math.max(0, (stream.estimatedCompletion - Date.now()) / 1000).toFixed(0)}s`
                              : "Calculating..."}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No active streams</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="system" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Memory Usage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {realTimeMetrics.memoryUsage.toFixed(1)}MB
                    </div>
                    <div className="text-xs text-muted-foreground">
                      JavaScript heap usage
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Total Requests</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {realTimeMetrics.totalRequests}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Since page load
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Bandwidth Usage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {formatBytes(realTimeMetrics.bandwidthUsage)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Current usage
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Session Duration</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {Math.floor(
                        (Date.now() - (realTimeMetrics.timestamp - 300000)) /
                          60000,
                      )}
                      m
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Time since dashboard opened
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="network" className="space-y-4">
              {connectionQuality ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Connection Quality
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2">
                      <NetworkIcon
                        className={cn(
                          "w-5 h-5",
                          getConnectionQualityColor(connectionQuality),
                        )}
                      />
                      <span className="font-medium">
                        {connectionQuality.effectiveType.toUpperCase()}
                      </span>
                    </div>

                    <Separator />

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Type:</span>
                        <div className="font-mono mt-1">
                          {connectionQuality.type}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">RTT:</span>
                        <div className="font-mono mt-1">
                          {connectionQuality.rtt}ms
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Downlink:</span>
                        <div className="font-mono mt-1">
                          {connectionQuality.downlink}Mbps
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          Save Data:
                        </span>
                        <div className="font-mono mt-1">
                          {connectionQuality.saveData ? "Yes" : "No"}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Connection information not available</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="history" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Performance Summary</CardTitle>
                  <CardDescription>
                    Overall performance metrics from the performance monitor
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Total streams processed:</span>
                      <span>{perf.getPerformanceSummary().totalStreams}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Average response time:</span>
                      <span>
                        {perf
                          .getPerformanceSummary()
                          .averageDuration.toFixed(0)}
                        ms
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Average chunks per stream:</span>
                      <span>
                        {perf.getPerformanceSummary().averageChunks.toFixed(1)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Error rate:</span>
                      <span>
                        {(perf.getPerformanceSummary().errorRate * 100).toFixed(
                          1,
                        )}
                        %
                      </span>
                    </div>
                  </div>

                  <Separator className="my-4" />

                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">
                      Performance Distribution
                    </h4>
                    {Object.entries(
                      perf.getPerformanceSummary().performanceDistribution,
                    ).map(([rating, count]) => (
                      <div
                        key={rating}
                        className="flex justify-between text-sm"
                      >
                        <span className="capitalize">{rating}:</span>
                        <span>{count}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}

        {/* Quick stats */}
        {!showDetails && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Memory:</span>
              <span>{realTimeMetrics.memoryUsage.toFixed(1)}MB</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Requests:</span>
              <span>{realTimeMetrics.totalRequests}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Errors:</span>
              <span>
                {Math.round(
                  (realTimeMetrics.totalRequests * realTimeMetrics.errorRate) /
                    100,
                )}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Connection:</span>
              <span className={getConnectionQualityColor(connectionQuality)}>
                {connectionQuality?.effectiveType?.toUpperCase() || "UNKNOWN"}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  },
);

StreamingDashboard.displayName = "StreamingDashboard";
