"""
AgenticFleet Performance Monitoring

Comprehensive monitoring system for load testing with real-time metrics,
performance analysis, and alerting capabilities.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""

    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    tags: dict[str, str]
    context: dict[str, Any] | None = None


@dataclass
class TestRunInfo:
    """Information about the current test run."""

    test_id: str
    test_name: str
    start_time: datetime
    environment: str
    target_url: str
    user_count: int
    test_type: str


class PerformanceMonitor:
    """
    Real-time performance monitoring for load testing.
    Collects system metrics, application metrics, and custom performance data.
    """

    def __init__(self, test_run_info: TestRunInfo):
        self.test_run_info = test_run_info
        self.metrics = defaultdict(list)
        self.metrics_history = deque(maxlen=10000)  # Keep last 10k metrics
        self.alerts = []
        self.is_running = False
        self.start_time = datetime.now()

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Prometheus metrics
        self.setup_prometheus_metrics()

        # System monitoring
        self.system_monitor_task = None
        self.application_health_monitor_task = None

        # Custom alerting rules
        self.alert_rules = {
            "error_rate": {"threshold": 5.0, "operator": "gt", "window": 60},
            "response_time_p95": {"threshold": 5000.0, "operator": "gt", "window": 60},
            "cpu_usage": {"threshold": 80.0, "operator": "gt", "window": 30},
            "memory_usage": {"threshold": 85.0, "operator": "gt", "window": 30},
            "active_users": {"threshold": 200, "operator": "gt", "window": 10},
        }

    def setup_prometheus_metrics(self):
        """Setup Prometheus metrics for monitoring."""
        # HTTP metrics
        self.http_requests_total = Counter(
            "agenticfleet_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        self.http_request_duration = Histogram(
            "agenticfleet_http_request_duration_ms",
            "HTTP request duration in milliseconds",
            ["method", "endpoint"],
            buckets=[10, 50, 100, 500, 1000, 5000, 10000, 30000],
        )

        # Chat-specific metrics
        self.chat_requests_total = Counter(
            "agenticfleet_chat_requests_total",
            "Total chat requests",
            ["conversation_id", "streaming"],
        )

        self.chat_response_time = Histogram(
            "agenticfleet_chat_response_time_ms",
            "Chat response time in milliseconds",
            ["streaming"],
            buckets=[100, 500, 1000, 2000, 5000, 10000, 20000, 60000],
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            "agenticfleet_system_cpu_usage_percent", "System CPU usage percentage"
        )

        self.system_memory_usage = Gauge(
            "agenticfleet_system_memory_usage_percent", "System memory usage percentage"
        )

        self.active_users = Gauge("agenticfleet_active_users", "Number of active users")

        # Error metrics
        self.error_rate = Gauge("agenticfleet_error_rate_percent", "Error rate percentage")

        # Workflow metrics
        self.workflow_requests_total = Counter(
            "agenticfleet_workflow_requests_total", "Total workflow requests", ["workflow_type"]
        )

        self.workflow_response_time = Histogram(
            "agenticfleet_workflow_response_time_ms",
            "Workflow response time in milliseconds",
            buckets=[50, 100, 200, 500, 1000, 2000, 5000],
        )

    async def start_monitoring(self):
        """Start the monitoring system."""
        self.is_running = True
        self.logger.info(f"Starting performance monitoring for test {self.test_run_info.test_id}")

        # Start Prometheus server
        try:
            start_http_server(9090)
            self.logger.info("Prometheus metrics server started on port 9090")
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")

        # Start system monitoring task
        self.system_monitor_task = asyncio.create_task(self.system_monitoring_loop())

        # Start application health monitoring (store task reference per RUF006)
        self.application_health_monitor_task = asyncio.create_task(
            self.application_health_monitor()
        )

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        self.is_running = False
        if self.system_monitor_task:
            self.system_monitor_task.cancel()
        if self.application_health_monitor_task:
            self.application_health_monitor_task.cancel()

        self.logger.info("Performance monitoring stopped")

    async def system_monitoring_loop(self):
        """Continuously monitor system metrics."""
        while self.is_running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_cpu_usage.set(cpu_percent)
                self.record_metric("cpu_usage", cpu_percent, "percent", {"source": "system"})

                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.system_memory_usage.set(memory_percent)
                self.record_metric("memory_usage", memory_percent, "percent", {"source": "system"})

                # Disk usage
                disk = psutil.disk_usage("/")
                disk_percent = (disk.used / disk.total) * 100
                self.record_metric("disk_usage", disk_percent, "percent", {"source": "system"})

                # Check alert rules
                await self.check_alert_rules()

            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")

            await asyncio.sleep(5)  # Monitor every 5 seconds

    async def application_health_monitor(self):
        """Monitor application health and availability."""
        while self.is_running:
            try:
                start_time = time.time()
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(
                        f"{self.test_run_info.target_url}/v1/system/health",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response,
                ):
                    response_time = (time.time() - start_time) * 1000
                    self.record_metric(
                        "health_check_response_time",
                        response_time,
                        "ms",
                        {
                            "endpoint": "health",
                            "status": f"{'healthy' if response.status == 200 else f'error_{response.status}'}",
                        },
                    )

                    if response.status == 200:
                        self.record_metric(
                            "health_check_success",
                            1,
                            "count",
                            {"endpoint": "health", "status": "healthy"},
                        )
                    else:
                        self.record_metric(
                            "health_check_failure",
                            1,
                            "count",
                            {"endpoint": "health", "status": f"error_{response.status}"},
                        )

            except Exception as e:
                self.record_metric(
                    "health_check_failure",
                    1,
                    "count",
                    {"endpoint": "health", "status": "unreachable"},
                )
                self.logger.error(f"Health check failed: {e}")

            await asyncio.sleep(30)  # Check health every 30 seconds

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        tags: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=name,
            value=value,
            unit=unit,
            tags=tags or {},
            context=context,
        )

        self.metrics[name].append(metric)
        self.metrics_history.append(metric)

        # Update Prometheus metrics
        self.update_prometheus_metrics(name, value, tags or {})

    def update_prometheus_metrics(self, name: str, value: float, tags: dict[str, str]):
        """Update Prometheus metrics based on the metric name."""
        if name == "http_request_duration":
            method = tags.get("method", "unknown")
            endpoint = tags.get("endpoint", "unknown")
            self.http_request_duration.labels(method=method, endpoint=endpoint).observe(value)
        elif name == "chat_response_time":
            streaming = tags.get("streaming", "false")
            self.chat_response_time.labels(streaming=streaming).observe(value)
        elif name == "active_users":
            self.active_users.set(value)
        elif name == "error_rate":
            self.error_rate.set(value)
        elif name == "workflow_response_time":
            self.workflow_response_time.observe(value)

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration_ms: float):
        """Record an HTTP request metric."""
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()

        self.record_metric(
            "http_request_duration",
            duration_ms,
            "ms",
            {"method": method, "endpoint": endpoint, "status": str(status_code)},
        )

    def record_chat_request(
        self, conversation_id: str, streaming: bool, response_time_ms: float, success: bool
    ):
        """Record a chat request metric."""
        self.chat_requests_total.labels(
            conversation_id=conversation_id, streaming=str(streaming).lower()
        ).inc()

        self.record_metric(
            "chat_response_time",
            response_time_ms,
            "ms",
            {"streaming": str(streaming).lower(), "success": str(success)},
        )

    def record_workflow_request(self, workflow_type: str, response_time_ms: float):
        """Record a workflow request metric."""
        self.workflow_requests_total.labels(workflow_type=workflow_type).inc()
        self.workflow_response_time.observe(response_time_ms)

    def update_active_users(self, user_count: int):
        """Update the active user count."""
        self.active_users.set(user_count)
        self.record_metric("active_users", user_count, "count")

    async def check_alert_rules(self):
        """Check alert rules and trigger alerts if necessary."""
        current_time = datetime.now()

        for rule_name, rule_config in self.alert_rules.items():
            if await self.evaluate_alert_rule(rule_name, rule_config, current_time):
                await self.trigger_alert(rule_name, rule_config)

    async def evaluate_alert_rule(
        self, rule_name: str, rule_config: dict, current_time: datetime
    ) -> bool:
        """Evaluate an alert rule."""
        threshold = rule_config["threshold"]
        operator = rule_config["operator"]
        window = rule_config["window"]

        # Get recent metrics for this rule
        cutoff_time = current_time - timedelta(seconds=window)
        recent_metrics = [
            m
            for m in self.metrics_history
            if m.metric_name == rule_name and m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return False

        # Calculate average value over the window
        values = [m.value for m in recent_metrics]
        avg_value = statistics.mean(values)

        # Evaluate the rule
        if operator == "gt":
            return avg_value > threshold
        elif operator == "lt":
            return avg_value < threshold
        elif operator == "eq":
            return abs(avg_value - threshold) < 0.01
        else:
            return False

    async def trigger_alert(self, rule_name: str, rule_config: dict):
        """Trigger an alert."""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "rule_name": rule_name,
            "threshold": rule_config["threshold"],
            "operator": rule_config["operator"],
            "test_id": self.test_run_info.test_id,
            "severity": "warning" if rule_name in ["cpu_usage", "memory_usage"] else "critical",
        }

        self.alerts.append(alert)
        self.logger.warning(f"ALERT TRIGGERED: {rule_name} threshold exceeded")

        # In a real implementation, you might send this to Slack, PagerDuty, etc.
        # For now, we'll just log it

    def get_performance_summary(self) -> dict[str, Any]:
        """Get a performance summary for the current test run."""
        duration = datetime.now() - self.start_time

        # Calculate metrics
        total_requests = len(
            [m for m in self.metrics_history if m.metric_name == "http_request_duration"]
        )
        error_metrics = [
            m
            for m in self.metrics_history
            if m.metric_name == "http_request_duration" and m.tags.get("status", "200") != "200"
        ]
        error_rate = (len(error_metrics) / total_requests * 100) if total_requests > 0 else 0

        response_times = [
            m.value for m in self.metrics_history if m.metric_name == "http_request_duration"
        ]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = (
            statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0
        )

        chat_response_times = [
            m.value for m in self.metrics_history if m.metric_name == "chat_response_time"
        ]
        avg_chat_time = statistics.mean(chat_response_times) if chat_response_times else 0

        return {
            "test_run": asdict(self.test_run_info),
            "duration_seconds": duration.total_seconds(),
            "total_requests": total_requests,
            "error_rate_percent": round(error_rate, 2),
            "avg_response_time_ms": round(avg_response_time, 2),
            "p95_response_time_ms": round(p95_response_time, 2),
            "avg_chat_response_time_ms": round(avg_chat_time, 2),
            "active_users": self.active_users._value._value,
            "system_cpu_usage": self.system_cpu_usage._value._value,
            "system_memory_usage": self.system_memory_usage._value._value,
            "alerts_triggered": len(self.alerts),
            "alerts": self.alerts[-5:],  # Last 5 alerts
        }

    def export_metrics(self, export_format: str = "json") -> str:
        """Export metrics in the specified format."""
        if export_format == "json":
            return json.dumps(
                {
                    "test_run": asdict(self.test_run_info),
                    "metrics": [asdict(m) for m in self.metrics_history],
                    "alerts": self.alerts,
                    "summary": self.get_performance_summary(),
                },
                default=str,
                indent=2,
            )
        else:
            raise ValueError(f"Unsupported export format: {export_format}")


class MetricsCollector:
    """Collects and aggregates metrics from various sources."""

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.aggregated_metrics = defaultdict(list)

    async def collect_locust_metrics(
        self, locust_stats_url: str = "http://localhost:8089/stats/requests"
    ):
        """Collect metrics from Locust web interface."""
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(locust_stats_url) as response,
            ):
                if response.status == 200:
                    stats = await response.json()
                    await self.process_locust_stats(stats)
        except Exception as e:
            print(f"Error collecting Locust metrics: {e}")

    async def process_locust_stats(self, stats: dict):
        """Process Locust statistics and convert to our format."""
        for request_type, data in stats.get("requests", {}).items():
            # Record request counts and response times
            self.monitor.record_metric(
                "locust_request_count",
                data.get("num_requests", 0),
                "count",
                {"request_type": request_type},
            )

            self.monitor.record_metric(
                "locust_response_time",
                data.get("median_response_time", 0),
                "ms",
                {"request_type": request_type, "percentile": "50"},
            )

    async def collect_system_logs(self, log_file_path: str = "/var/log/agentic_fleet.log"):
        """Parse and collect metrics from application logs."""
        # This would implement log parsing logic
        # For now, it's a placeholder
        pass


# Utility functions for running the monitor
def create_test_run_info(
    test_name: str, environment: str, target_url: str, user_count: int, test_type: str = "load"
) -> TestRunInfo:
    """Create test run information."""
    import uuid

    return TestRunInfo(
        test_id=str(uuid.uuid4()),
        test_name=test_name,
        start_time=datetime.now(),
        environment=environment,
        target_url=target_url,
        user_count=user_count,
        test_type=test_type,
    )


async def run_monitoring_session(test_run_info: TestRunInfo, duration_minutes: int = 10):
    """Run a monitoring session for the specified duration."""
    monitor = PerformanceMonitor(test_run_info)

    try:
        await monitor.start_monitoring()

        # Run for specified duration
        await asyncio.sleep(duration_minutes * 60)

    finally:
        await monitor.stop_monitoring()

        # Print summary
        summary = monitor.get_performance_summary()
        print("\n" + "=" * 50)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 50)
        print(json.dumps(summary, indent=2, default=str))
        print("=" * 50)

    return monitor


if __name__ == "__main__":
    # Example usage
    test_info = create_test_run_info(
        test_name="example_load_test",
        environment="local",
        target_url="http://localhost:8000",
        user_count=50,
        test_type="load",
    )

    # Run monitoring for 5 minutes
    asyncio.run(run_monitoring_session(test_info, 5))
