// Performance monitoring utilities for AgenticFleet chat interface

export interface PerformanceMetrics {
  // Timing metrics
  requestStartTime: number;
  firstByteTime?: number;
  firstChunkTime?: number;
  completionTime?: number;

  // Streaming metrics
  totalChunks: number;
  averageChunkInterval: number;
  maxChunkInterval: number;
  minChunkInterval: number;

  // Network metrics
  connectionType?: string;
  effectiveBandwidth?: number;
  roundTripTime?: number;

  // User interaction metrics
  timeToFirstInteraction: number;
  interactionLatency: number;
  errorRecoveryTime?: number;

  // System metrics
  memoryUsage?: number;
  cpuUsage?: number;
}

export interface StreamingPerformanceData {
  messageId: string;
  conversationId: string;
  agentName?: string;
  startTime: number;
  chunks: Array<{
    timestamp: number;
    size: number;
    content: string;
  }>;
  errors: Array<{
    timestamp: number;
    error: string;
    recovered: boolean;
  }>;
}

class PerformanceMonitor {
  private activeStreams = new Map<string, StreamingPerformanceData>();
  private metrics: PerformanceMetrics[] = [];
  private observers: PerformanceObserver[] = [];

  constructor() {
    this.setupPerformanceObservers();
    this.startMetricsCollection();
  }

  private setupPerformanceObservers() {
    // Observe navigation timing
    if ("PerformanceObserver" in window) {
      const navObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === "navigation") {
            const navEntry = entry as PerformanceNavigationTiming;
            console.log("Navigation performance:", {
              domContentLoaded:
                navEntry.domContentLoadedEventEnd -
                navEntry.domContentLoadedEventStart,
              loadComplete: navEntry.loadEventEnd - navEntry.loadEventStart,
              firstPaint: navEntry.responseEnd - navEntry.requestStart,
            });
          }
        }
      });
      navObserver.observe({ entryTypes: ["navigation"] });
      this.observers.push(navObserver);

      // Observe resource timing
      const resourceObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === "resource") {
            const resource = entry as PerformanceResourceTiming;
            if (
              resource.name.includes("/v1/chat") ||
              resource.name.includes("/v1/conversations")
            ) {
              console.log("API resource performance:", {
                url: resource.name,
                duration: resource.duration,
                size: resource.transferSize,
                cached:
                  resource.transferSize === 0 && resource.decodedBodySize > 0,
              });
            }
          }
        }
      });
      resourceObserver.observe({ entryTypes: ["resource"] });
      this.observers.push(resourceObserver);
    }
  }

  private startMetricsCollection() {
    // Collect memory metrics every 30 seconds
    setInterval(() => {
      if ("memory" in performance) {
        const memory = (performance as any).memory;
        console.log("Memory usage:", {
          used: Math.round(memory.usedJSHeapSize / 1024 / 1024) + "MB",
          total: Math.round(memory.totalJSHeapSize / 1024 / 1024) + "MB",
          limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024) + "MB",
        });
      }
    }, 30000);

    // Monitor connection quality
    this.monitorConnectionQuality();
  }

  private monitorConnectionQuality() {
    if ("connection" in navigator) {
      const connection = (navigator as any).connection;
      console.log("Connection info:", {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
      });

      connection.addEventListener("change", () => {
        console.log("Connection changed:", {
          effectiveType: connection.effectiveType,
          downlink: connection.downlink,
          rtt: connection.rtt,
        });
      });
    }
  }

  // Stream monitoring
  startStreamMonitoring(
    messageId: string,
    conversationId: string,
    agentName?: string,
  ): void {
    const data: StreamingPerformanceData = {
      messageId,
      conversationId,
      agentName,
      startTime: performance.now(),
      chunks: [],
      errors: [],
    };

    this.activeStreams.set(messageId, data);
  }

  recordStreamChunk(messageId: string, content: string): void {
    const stream = this.activeStreams.get(messageId);
    if (!stream) return;

    const now = performance.now();
    const chunkData = {
      timestamp: now,
      size: content.length,
      content,
    };

    stream.chunks.push(chunkData);

    // Log performance warnings
    if (stream.chunks.length > 1) {
      const lastChunk = stream.chunks[stream.chunks.length - 2];
      const interval = now - lastChunk.timestamp;

      if (interval > 5000) {
        console.warn(
          `Slow chunk detected: ${interval}ms interval for message ${messageId}`,
        );
      }
    }
  }

  recordStreamError(messageId: string, error: string, recovered = false): void {
    const stream = this.activeStreams.get(messageId);
    if (!stream) return;

    stream.errors.push({
      timestamp: performance.now(),
      error,
      recovered,
    });

    console.error(`Stream error for message ${messageId}:`, error);
  }

  endStreamMonitoring(messageId: string): PerformanceMetrics | null {
    const stream = this.activeStreams.get(messageId);
    if (!stream) return null;

    const endTime = performance.now();
    const duration = endTime - stream.startTime;

    // Calculate metrics
    const metrics: PerformanceMetrics = {
      requestStartTime: stream.startTime,
      completionTime: endTime,
      totalChunks: stream.chunks.length,
      averageChunkInterval:
        stream.chunks.length > 1
          ? this.calculateAverageInterval(stream.chunks)
          : 0,
      maxChunkInterval: this.calculateMaxInterval(stream.chunks),
      minChunkInterval: this.calculateMinInterval(stream.chunks),
      timeToFirstInteraction: 0, // To be set by interaction tracking
      interactionLatency: 0,
    };

    // Log comprehensive performance data
    console.group(`📊 Stream Performance: ${messageId}`);
    console.log("Duration:", `${duration.toFixed(2)}ms`);
    console.log("Total chunks:", stream.chunks.length);
    console.log(
      "Average chunk interval:",
      `${metrics.averageChunkInterval.toFixed(2)}ms`,
    );
    console.log(
      "Max chunk interval:",
      `${metrics.maxChunkInterval.toFixed(2)}ms`,
    );
    console.log(
      "Min chunk interval:",
      `${metrics.minChunkInterval.toFixed(2)}ms`,
    );
    console.log("Errors:", stream.errors.length);

    if (stream.errors.length > 0) {
      console.log("Error details:", stream.errors);
    }

    // Performance classification
    const performance = this.classifyPerformance(metrics);
    console.log(
      "Performance rating:",
      performance.emoji,
      performance.rating,
      performance.description,
    );
    console.groupEnd();

    this.metrics.push(metrics);
    this.activeStreams.delete(messageId);

    return metrics;
  }

  private calculateAverageInterval(
    chunks: Array<{ timestamp: number }>,
  ): number {
    if (chunks.length < 2) return 0;

    let totalInterval = 0;
    for (let i = 1; i < chunks.length; i++) {
      totalInterval += chunks[i].timestamp - chunks[i - 1].timestamp;
    }

    return totalInterval / (chunks.length - 1);
  }

  private calculateMaxInterval(chunks: Array<{ timestamp: number }>): number {
    if (chunks.length < 2) return 0;

    let maxInterval = 0;
    for (let i = 1; i < chunks.length; i++) {
      const interval = chunks[i].timestamp - chunks[i - 1].timestamp;
      maxInterval = Math.max(maxInterval, interval);
    }

    return maxInterval;
  }

  private calculateMinInterval(chunks: Array<{ timestamp: number }>): number {
    if (chunks.length < 2) return 0;

    let minInterval = Infinity;
    for (let i = 1; i < chunks.length; i++) {
      const interval = chunks[i].timestamp - chunks[i - 1].timestamp;
      minInterval = Math.min(minInterval, interval);
    }

    return minInterval === Infinity ? 0 : minInterval;
  }

  private classifyPerformance(metrics: PerformanceMetrics): {
    emoji: string;
    rating: "excellent" | "good" | "fair" | "poor";
    description: string;
  } {
    const duration = metrics.completionTime! - metrics.requestStartTime;
    const avgInterval = metrics.averageChunkInterval;
    const errorCount =
      this.metrics.length > 0
        ? this.metrics[this.metrics.length - 1].totalChunks
        : 0;

    if (duration < 1000 && avgInterval < 100 && errorCount === 0) {
      return {
        emoji: "🚀",
        rating: "excellent",
        description:
          "Excellent performance - fast response with smooth streaming",
      };
    } else if (duration < 3000 && avgInterval < 500 && errorCount === 0) {
      return {
        emoji: "✅",
        rating: "good",
        description: "Good performance - reasonable response time",
      };
    } else if (duration < 10000 && avgInterval < 2000) {
      return {
        emoji: "⚠️",
        rating: "fair",
        description: "Fair performance - some delays detected",
      };
    } else {
      return {
        emoji: "❌",
        rating: "poor",
        description: "Poor performance - significant delays or issues",
      };
    }
  }

  // User interaction tracking
  trackInteraction(action: string, startTime: number): void {
    const endTime = performance.now();
    const latency = endTime - startTime;

    console.log(`🖱️ Interaction: ${action} took ${latency.toFixed(2)}ms`);

    // Track slow interactions
    if (latency > 100) {
      console.warn(
        `Slow interaction detected: ${action} took ${latency.toFixed(2)}ms`,
      );
    }
  }

  // Error tracking
  trackError(error: Error, context?: string): void {
    const errorData = {
      message: error.message,
      stack: error.stack,
      context,
      timestamp: performance.now(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    console.error("💥 Error tracked:", errorData);

    // Here you could send to error reporting service
    // sendErrorToService(errorData);
  }

  // Get performance summary
  getPerformanceSummary(): {
    totalStreams: number;
    averageDuration: number;
    averageChunks: number;
    errorRate: number;
    performanceDistribution: Record<string, number>;
  } {
    if (this.metrics.length === 0) {
      return {
        totalStreams: 0,
        averageDuration: 0,
        averageChunks: 0,
        errorRate: 0,
        performanceDistribution: {},
      };
    }

    const durations = this.metrics.map(
      (m) => m.completionTime! - m.requestStartTime,
    );
    const totalChunks = this.metrics.reduce((sum, m) => sum + m.totalChunks, 0);
    const errorRate =
      this.metrics.filter((m) => m.errorRecoveryTime !== undefined).length /
      this.metrics.length;

    const performanceDistribution = this.metrics.reduce(
      (acc, m) => {
        const duration = m.completionTime! - m.requestStartTime;
        let category: string;

        if (duration < 1000) category = "excellent";
        else if (duration < 3000) category = "good";
        else if (duration < 10000) category = "fair";
        else category = "poor";

        acc[category] = (acc[category] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      totalStreams: this.metrics.length,
      averageDuration: durations.reduce((a, b) => a + b, 0) / durations.length,
      averageChunks: totalChunks / this.metrics.length,
      errorRate,
      performanceDistribution,
    };
  }

  // Cleanup
  cleanup(): void {
    this.observers.forEach((observer) => observer.disconnect());
    this.observers = [];
    this.activeStreams.clear();
  }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Export hooks for React components
export const usePerformanceMonitor = () => {
  const startInteraction = (action: string) => {
    const startTime = performance.now();
    return () => performanceMonitor.trackInteraction(action, startTime);
  };

  return {
    startStreamMonitoring:
      performanceMonitor.startStreamMonitoring.bind(performanceMonitor),
    recordStreamChunk:
      performanceMonitor.recordStreamChunk.bind(performanceMonitor),
    recordStreamError:
      performanceMonitor.recordStreamError.bind(performanceMonitor),
    endStreamMonitoring:
      performanceMonitor.endStreamMonitoring.bind(performanceMonitor),
    startInteraction,
    trackError: performanceMonitor.trackError.bind(performanceMonitor),
    getPerformanceSummary:
      performanceMonitor.getPerformanceSummary.bind(performanceMonitor),
  };
};

export default performanceMonitor;
