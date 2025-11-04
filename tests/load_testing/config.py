"""
AgenticFleet Load Testing Configuration

Central configuration for load testing parameters, scenarios, and targets.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class TestType(Enum):
    """Types of load tests."""

    SMOKE = "smoke"
    LOAD = "load"
    STRESS = "stress"
    SPIKE = "spike"
    ENDURANCE = "endurance"
    CAPACITY = "capacity"


class TestEnvironment(Enum):
    """Test environments."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class TestTarget:
    """Test target configuration."""

    name: str
    url: str
    description: str
    weight: float = 1.0


@dataclass
class TestScenario:
    """Load test scenario configuration."""

    name: str
    description: str
    users: int
    spawn_rate: int
    duration: str  # e.g., "10s", "5m", "1h"
    test_type: TestType
    targets: list[TestTarget]
    custom_options: dict | None = None


class LoadTestConfig:
    """Main configuration class for load testing."""

    def __init__(self, environment: TestEnvironment = TestEnvironment.LOCAL):
        self.environment = environment
        self.base_urls = self._get_base_urls()
        self.auth_config = self._get_auth_config()
        self.scenarios = self._get_scenarios()
        self.monitoring_config = self._get_monitoring_config()

    def _get_base_urls(self) -> dict[TestEnvironment, str]:
        """Get base URLs for different environments."""
        return {
            TestEnvironment.LOCAL: "http://localhost:8000",
            TestEnvironment.DEVELOPMENT: os.getenv(
                "DEV_API_URL", "https://dev-api.agenticfleet.com"
            ),
            TestEnvironment.STAGING: os.getenv(
                "STAGING_API_URL", "https://staging-api.agenticfleet.com"
            ),
            TestEnvironment.PRODUCTION: os.getenv("PROD_API_URL", "https://api.agenticfleet.com"),
        }

    def _get_auth_config(self) -> dict:
        """Get authentication configuration."""
        return {
            "api_key": os.getenv("AGENTICFLEET_API_KEY"),
            "auth_header": "Authorization",
            "auth_type": "Bearer",  # or "Basic", etc.
        }

    def _get_scenarios(self) -> list[TestScenario]:
        """Define test scenarios."""
        return [
            # Smoke tests - quick validation
            TestScenario(
                name="smoke_test",
                description="Quick smoke test to validate basic functionality",
                users=5,
                spawn_rate=1,
                duration="30s",
                test_type=TestType.SMOKE,
                targets=[
                    TestTarget("health_check", "/v1/system/health", "Basic health check"),
                    TestTarget("workflows", "/v1/workflows", "List workflows"),
                    TestTarget("simple_chat", "/v1/chat", "Simple chat message"),
                ],
            ),
            # Load tests - normal expected load
            TestScenario(
                name="normal_load",
                description="Simulate normal user load",
                users=50,
                spawn_rate=5,
                duration="5m",
                test_type=TestType.LOAD,
                targets=[
                    TestTarget("chat", "/v1/chat", "Chat interactions", weight=3.0),
                    TestTarget("streaming_chat", "/v1/chat", "Streaming chat", weight=2.0),
                    TestTarget("workflows", "/v1/workflows", "Workflow operations", weight=1.0),
                    TestTarget("health_check", "/v1/system/health", "Health checks", weight=0.5),
                ],
            ),
            # Stress tests - beyond normal capacity
            TestScenario(
                name="stress_test",
                description="Test system behavior under stress",
                users=200,
                spawn_rate=20,
                duration="10m",
                test_type=TestType.STRESS,
                targets=[
                    TestTarget("chat", "/v1/chat", "High-volume chat", weight=4.0),
                    TestTarget("streaming_chat", "/v1/chat", "Concurrent streaming", weight=3.0),
                    TestTarget("workflows", "/v1/workflows", "Workflow stress", weight=1.0),
                ],
            ),
            # Spike tests - sudden load spikes
            TestScenario(
                name="spike_test",
                description="Test system response to sudden load spikes",
                users=5,
                spawn_rate=1,
                duration="2m",
                test_type=TestType.SPIKE,
                custom_options={
                    "spike_users": 150,
                    "spike_duration": "30s",
                    "spike_spawn_rate": 50,
                },
                targets=[
                    TestTarget("chat", "/v1/chat", "Spike chat load", weight=5.0),
                    TestTarget("streaming_chat", "/v1/chat", "Spike streaming", weight=3.0),
                ],
            ),
            # Endurance tests - sustained load
            TestScenario(
                name="endurance_test",
                description="Test system stability under sustained load",
                users=30,
                spawn_rate=3,
                duration="30m",
                test_type=TestType.ENDURANCE,
                targets=[
                    TestTarget("chat", "/v1/chat", "Sustained chat usage", weight=2.0),
                    TestTarget("streaming_chat", "/v1/chat", "Sustained streaming", weight=1.5),
                    TestTarget("workflows", "/v1/workflows", "Workflow endurance", weight=1.0),
                    TestTarget(
                        "health_check", "/v1/system/health", "Health monitoring", weight=0.3
                    ),
                ],
            ),
            # Capacity planning
            TestScenario(
                name="capacity_test",
                description="Gradually increase load to find capacity limits",
                users=10,
                spawn_rate=2,
                duration="15m",
                test_type=TestType.CAPACITY,
                custom_options={
                    "max_users": 300,
                    "step_users": 25,
                    "step_duration": "2m",
                },
                targets=[
                    TestTarget("chat", "/v1/chat", "Capacity testing chat", weight=3.0),
                    TestTarget("streaming_chat", "/v1/chat", "Capacity streaming", weight=2.0),
                ],
            ),
        ]

    def _get_monitoring_config(self) -> dict:
        """Get monitoring and metrics configuration."""
        return {
            "enable_real_time_metrics": True,
            "metrics_interval": 5,  # seconds
            "enable_detailed_logging": True,
            "log_level": "INFO",
            "export_metrics": {
                "prometheus": os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true",
                "prometheus_port": 9090,
                "grafana": os.getenv("GRAFANA_ENABLED", "false").lower() == "true",
                "influxdb": os.getenv("INFLUXDB_ENABLED", "false").lower() == "true",
            },
            "alerting": {
                "error_rate_threshold": 5.0,  # percentage
                "response_time_threshold": 5000,  # milliseconds
                "failure_rate_threshold": 10.0,  # percentage
            },
            "system_monitoring": {
                "cpu_threshold": 80.0,  # percentage
                "memory_threshold": 85.0,  # percentage
                "disk_threshold": 90.0,  # percentage
            },
        }

    def get_base_url(self) -> str:
        """Get the base URL for the current environment."""
        return self.base_urls[self.environment]

    def get_scenario(self, name: str) -> TestScenario | None:
        """Get a specific scenario by name."""
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario
        return None

    def get_scenario_names(self) -> list[str]:
        """Get all available scenario names."""
        return [scenario.name for scenario in self.scenarios]

    def is_auth_required(self) -> bool:
        """Check if authentication is required for the current environment."""
        return self.environment in [
            TestEnvironment.DEVELOPMENT,
            TestEnvironment.STAGING,
            TestEnvironment.PRODUCTION,
        ]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        if self.is_auth_required() and self.auth_config["api_key"]:
            return {
                self.auth_config[
                    "auth_header"
                ]: f"{self.auth_config['auth_type']} {self.auth_config['api_key']}"
            }
        return {}


# Test data for load testing
class TestData:
    """Static test data for load testing scenarios.

    Class-level constants annotated with ClassVar to satisfy RUF012 (mutable class attributes).
    These containers are treated as read-only test fixtures.
    """

    CHAT_MESSAGES: ClassVar[list[str]] = [
        "What are the key principles of microservices architecture?",
        "Explain the benefits of using FastAPI for web development",
        "How do I optimize database queries for better performance?",
        "What are the best practices for API authentication?",
        "Can you help me design a scalable system architecture?",
        "What are the differences between SQL and NoSQL databases?",
        "How do I implement proper error handling in distributed systems?",
        "What are the key considerations for system monitoring and observability?",
        "Explain the concept of eventual consistency in distributed systems",
        "How do I design a RESTful API that follows best practices?",
        "What are the common patterns for handling database transactions?",
        "How do I implement caching strategies effectively?",
        "What are the principles of domain-driven design?",
        "How do I ensure data consistency across microservices?",
        "What are the best practices for API versioning?",
    ]

    WORKFLOW_QUERIES: ClassVar[list[str]] = [
        "What workflows are available?",
        "Show me the magentic fleet workflow configuration",
        "Get details for the workflow system",
        "List all available workflows with their configurations",
    ]

    USER_CONTEXTS: ClassVar[list[dict[str, str]]] = [
        {"role": "developer", "experience": "intermediate"},
        {"role": "architect", "experience": "senior"},
        {"role": "student", "experience": "beginner"},
        {"role": "team_lead", "experience": "senior"},
        {"role": "devops", "experience": "intermediate"},
    ]

    @classmethod
    def get_random_message(cls) -> str:
        """Get a random chat message."""
        import random

        return random.choice(cls.CHAT_MESSAGES)

    @classmethod
    def get_random_user_context(cls) -> dict:
        """Get a random user context."""
        import random

        return random.choice(cls.USER_CONTEXTS)


# Default configuration instance
DEFAULT_CONFIG = LoadTestConfig()
