#!/usr/bin/env python3
"""
AgenticFleet Load Testing Runner

Main script for running load tests with comprehensive monitoring,
reporting, and analysis capabilities.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# Add parent directory to path to import config and monitoring
sys.path.append(str(Path(__file__).parent))

from monitoring import create_test_run_info, run_monitoring_session
from tests.load_testing.config import LoadTestConfig, TestEnvironment


class TestResult(BaseModel):
    """Model for test results."""

    test_id: str
    test_name: str
    test_type: str
    environment: str
    start_time: datetime
    end_time: datetime | None = None
    status: str  # "running", "completed", "failed", "cancelled"
    metrics: dict[str, Any] = {}
    summary: dict[str, Any] = {}


class LoadTestRunner:
    """
    Main load testing orchestrator that coordinates test execution,
    monitoring, and reporting.
    """

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file
        self.config = self._load_config()
        self.active_tests: dict[str, TestResult] = {}
        self.monitor = None

    def _load_config(self) -> LoadTestConfig:
        """Load configuration from file or use defaults."""
        if self.config_file and Path(self.config_file).exists():
            with open(self.config_file) as f:
                config_data = yaml.safe_load(f)
                # Convert dict to config object (simplified)
                if config_data is not None:
                    return LoadTestConfig(**config_data)
                else:
                    return LoadTestConfig()
        return LoadTestConfig()

    async def run_locust_test(
        self, scenario_name: str, users: int, spawn_rate: int, duration: str, host: str
    ):
        """Run a Locust-based load test."""
        print(f"Starting Locust test: {scenario_name}")
        print(f"Users: {users}, Spawn Rate: {spawn_rate}, Duration: {duration}")
        print(f"Target: {host}")

        # Create test run info
        test_run_info = create_test_run_info(
            test_name=scenario_name,
            environment=self.config.environment.value,
            target_url=host,
            user_count=users,
            test_type="locust_load",
        )

        # Start monitoring
        monitor_task = asyncio.create_task(self._run_monitoring(test_run_info, duration))

        # Run Locust test
        locust_cmd = [
            "locust",
            "-f",
            "locustfile.py",
            "--host",
            host,
            "--users",
            str(users),
            "--spawn-rate",
            str(spawn_rate),
            "--run-time",
            duration,
            "--headless",  # Run without web UI for automated testing
            "--html",
            f"reports/{scenario_name}_report.html",
            "--csv",
            f"reports/{scenario_name}_stats",
        ]

        try:
            # Create reports directory if it doesn't exist
            Path("reports").mkdir(exist_ok=True)

            # Run Locust
            process = await asyncio.create_subprocess_exec(
                *locust_cmd,
                cwd=Path(__file__).parent,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print("Locust test completed successfully")
                return True
            else:
                print(f"Locust test failed with return code {process.returncode}")
                print(f"Error: {stderr.decode()}")
                return False

        except Exception as e:
            print(f"Error running Locust test: {e}")
            return False

        finally:
            monitor_task.cancel()

    async def run_k6_test(self, script_file: str, options: dict[str, Any]):
        """Run a k6-based load test."""
        print(f"Starting k6 test with script: {script_file}")

        # Build k6 command
        k6_cmd = ["k6", "run", script_file]

        # Add environment variables
        env_vars = {
            "BASE_URL": options.get("base_url", "http://localhost:8000"),
            "VUS": str(options.get("users", 50)),
        }

        # Add options as command line arguments
        if "stages" in options:
            # Convert stages to JSON string
            k6_cmd.extend(["--", json.dumps({"stages": options["stages"]})])

        try:
            # Create environment for subprocess
            env = os.environ.copy()
            env.update(env_vars)

            # Run k6
            process = await asyncio.create_subprocess_exec(
                *k6_cmd,
                cwd=Path(__file__).parent,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print("k6 test completed successfully")
                return True
            else:
                print(f"k6 test failed with return code {process.returncode}")
                print(f"Error: {stderr.decode()}")
                return False

        except Exception as e:
            print(f"Error running k6 test: {e}")
            return False

    async def _run_monitoring(self, test_run_info, duration_str: str):
        """Run monitoring for the duration of the test."""
        try:
            # Parse duration (e.g., "5m", "30s", "1h")
            duration_seconds = self._parse_duration(duration_str)

            # Run monitoring session
            monitor = await run_monitoring_session(test_run_info, duration_seconds // 60)

            # Export metrics
            metrics_file = f"reports/{test_run_info.test_name}_metrics.json"
            with open(metrics_file, "w") as f:
                f.write(monitor.export_metrics())

            print(f"Metrics exported to {metrics_file}")

        except Exception as e:
            print(f"Error in monitoring: {e}")

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds."""
        duration_str = duration_str.lower().strip()
        if duration_str.endswith("s"):
            return int(duration_str[:-1])
        elif duration_str.endswith("m"):
            return int(duration_str[:-1]) * 60
        elif duration_str.endswith("h"):
            return int(duration_str[:-1]) * 3600
        else:
            # Assume seconds
            return int(duration_str)

    async def run_predefined_scenario(self, scenario_name: str):
        """Run a predefined test scenario."""
        scenario = self.config.get_scenario(scenario_name)
        if not scenario:
            print(f"Scenario '{scenario_name}' not found")
            return False

        print(f"Running scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Type: {scenario.test_type.value}")
        print(f"Users: {scenario.users}, Duration: {scenario.duration}")

        host = self.config.get_base_url()

        # Add authentication headers if required
        auth_headers = self.config.get_auth_headers()
        if auth_headers:
            # Set environment variables for Locust/k6
            os.environ["AUTH_HEADERS"] = json.dumps(auth_headers)

        return await self.run_locust_test(
            scenario.name, scenario.users, scenario.spawn_rate, scenario.duration, host
        )

    async def run_health_check(self):
        """Run a quick health check to ensure the system is ready for testing."""
        print("Running system health check...")

        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                # Check main API
                async with session.get(
                    f"{self.config.get_base_url()}/v1/system/health",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        print("✅ API health check passed")
                    else:
                        print(f"❌ API health check failed: {response.status}")
                        return False

                # Check workflows endpoint
                async with session.get(
                    f"{self.config.get_base_url()}/v1/workflows",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        print("✅ Workflows endpoint accessible")
                    else:
                        print(f"❌ Workflows endpoint failed: {response.status}")
                        return False

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

        return True

    def generate_report(self, test_results: list[TestResult]):
        """Generate a comprehensive test report."""
        report = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "environment": self.config.environment.value,
                "total_tests": len(test_results),
            },
            "summary": {
                "successful_tests": len([t for t in test_results if t.status == "completed"]),
                "failed_tests": len([t for t in test_results if t.status == "failed"]),
                "total_duration": sum(
                    [
                        (t.end_time - t.start_time).total_seconds()
                        for t in test_results
                        if t.end_time
                    ]
                )
                if test_results
                else 0,
            },
            "results": [result.dict() for result in test_results],
            "recommendations": self._generate_recommendations(test_results),
        }

        # Save report
        report_file = f"reports/load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("reports").mkdir(exist_ok=True)
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Report generated: {report_file}")
        return report_file

    def _generate_recommendations(self, test_results: list[TestResult]) -> list[str]:
        """Generate performance recommendations based on test results."""
        recommendations = []

        for result in test_results:
            if result.metrics:
                # Check response times
                avg_response_time = result.metrics.get("avg_response_time_ms", 0)
                if avg_response_time > 5000:
                    recommendations.append(
                        f"High average response time detected in {result.test_name}: {avg_response_time}ms. "
                        "Consider optimizing API performance or adding caching."
                    )

                # Check error rates
                error_rate = result.metrics.get("error_rate_percent", 0)
                if error_rate > 5:
                    recommendations.append(
                        f"High error rate in {result.test_name}: {error_rate}%. "
                        "Investigate error patterns and improve error handling."
                    )

                # Check system resources
                cpu_usage = result.metrics.get("system_cpu_usage", 0)
                if cpu_usage > 80:
                    recommendations.append(
                        f"High CPU usage during {result.test_name}: {cpu_usage}%. "
                        "Consider scaling up or optimizing CPU-intensive operations."
                    )

                memory_usage = result.metrics.get("system_memory_usage", 0)
                if memory_usage > 85:
                    recommendations.append(
                        f"High memory usage during {result.test_name}: {memory_usage}%. "
                        "Investigate memory leaks or optimize memory usage."
                    )

        if not recommendations:
            recommendations.append("All performance metrics are within acceptable ranges.")

        return recommendations


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AgenticFleet Load Testing Runner")
    parser.add_argument("--scenario", help="Test scenario to run", default="smoke_test")
    parser.add_argument(
        "--tool", choices=["locust", "k6"], default="locust", help="Testing tool to use"
    )
    parser.add_argument("--users", type=int, help="Number of users")
    parser.add_argument("--spawn-rate", type=int, help="User spawn rate")
    parser.add_argument("--duration", help="Test duration (e.g., 5m, 30s, 1h)")
    parser.add_argument(
        "--environment", choices=["local", "development", "staging", "production"], default="local"
    )
    parser.add_argument("--host", help="Target host URL")
    parser.add_argument(
        "--health-check", action="store_true", help="Run health check before testing"
    )
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")

    args = parser.parse_args()

    # Initialize success flag to avoid possible 'unbound' warnings.
    success = False

    # Create runner
    runner = LoadTestRunner()
    runner.config.environment = TestEnvironment(args.environment)

    if args.host:
        runner.config.base_urls[runner.config.environment] = args.host

    # List scenarios if requested
    if args.list_scenarios:
        print("Available test scenarios:")
        for scenario in runner.config.scenarios:
            print(f"  - {scenario.name}: {scenario.description}")
            print(f"    Users: {scenario.users}, Duration: {scenario.duration}")
        return

    # Run health check if requested
    if args.health_check and not await runner.run_health_check():
        print("Health check failed. Exiting.")
        return

    # Run test
    if args.tool == "locust":
        if args.scenario:
            success = await runner.run_predefined_scenario(args.scenario)
        else:
            # Custom test parameters
            success = await runner.run_locust_test(
                scenario_name="custom_test",
                users=args.users or 10,
                spawn_rate=args.spawn_rate or 2,
                duration=args.duration or "5m",
                host=runner.config.get_base_url(),
            )

    elif args.tool == "k6":
        k6_options = {
            "base_url": runner.config.get_base_url(),
            "users": args.users or 50,
            "stages": [
                {"duration": "2m", "target": 10},
                {"duration": "5m", "target": 50},
                {"duration": "3m", "target": 0},
            ],
        }
        success = await runner.run_k6_test("k6-chat-test.js", k6_options)

    if success:
        print("Load test completed successfully!")
    else:
        print("Load test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
