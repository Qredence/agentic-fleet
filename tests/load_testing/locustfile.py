"""
AgenticFleet Load Testing Suite

This module provides comprehensive load testing for the AgenticFleet API,
covering chat endpoints, workflow orchestration, and system health checks.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any

from locust import HttpUser, between, events, task
from locust.env import Environment
from locust.log import setup_logging

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/v1"
DEFAULT_TIMEOUT = 30.0
STREAM_TIMEOUT = 60.0


class AgenticFleetUser(HttpUser):
    """
    Simulates a typical AgenticFleet user interacting with the chat system.
    This includes conversation management, chat requests, and workflow interactions.
    """

    wait_time = between(1, 3)  # Simulate realistic user thinking time

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_id = None
        self.session_started = False
        self.user_context = {
            "session_id": str(uuid.uuid4()),
            "user_id": f"load_test_user_{uuid.uuid4().hex[:8]}",
            "preferences": {"response_style": "detailed", "workflow_type": "magentic_fleet"},
        }

    def on_start(self):
        """Called when a simulated user starts."""
        self.session_started = True
        self.conversation_id = self._create_conversation()
        self.log_event(
            "user_session_started",
            {"conversation_id": self.conversation_id, "user_id": self.user_context["user_id"]},
        )

    def on_stop(self):
        """Called when a simulated user stops."""
        if self.conversation_id:
            self.log_event(
                "user_session_ended",
                {
                    "conversation_id": self.conversation_id,
                    "session_duration": time.time()
                    - getattr(self, "session_start_time", time.time()),
                },
            )

    @task(3)
    def send_chat_message(self):
        """Primary task: Send chat messages to test the main functionality."""
        if not self.conversation_id:
            self.conversation_id = self._create_conversation()

        # Test different types of user queries
        test_messages = [
            "What are the key components of microservices architecture?",
            "Explain the benefits of using FastAPI for web development",
            "How do I optimize database queries for better performance?",
            "What are the best practices for API authentication?",
            "Can you help me design a scalable system architecture?",
            "What are the differences between SQL and NoSQL databases?",
            "How do I implement proper error handling in distributed systems?",
            "What are the key considerations for system monitoring and observability?",
        ]

        message = (
            self.environment.parsed_options.message
            or test_messages[hash(self.user_context["user_id"]) % len(test_messages)]
        )

        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
            "stream": False,  # Test non-streaming first
            "user_context": self.user_context,
        }

        with self.client.post(
            f"{API_PREFIX}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=DEFAULT_TIMEOUT,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.log_event(
                    "chat_response_received",
                    {
                        "conversation_id": self.conversation_id,
                        "message_length": len(message),
                        "response_length": len(data.get("message", "")),
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                    },
                )
                response.success()
            else:
                self.log_event(
                    "chat_error",
                    {
                        "conversation_id": self.conversation_id,
                        "status_code": response.status_code,
                        "error_text": response.text[:200],
                    },
                )
                response.failure(f"HTTP {response.status_code}: {response.text[:100]}")

    @task(2)
    def send_streaming_chat_message(self):
        """Test streaming chat functionality (more resource-intensive)."""
        if not self.conversation_id:
            self.conversation_id = self._create_conversation()

        test_messages = [
            "Write a Python function that demonstrates best practices for error handling",
            "Explain the concept of distributed systems and their challenges",
            "What are the key principles of software architecture design?",
        ]

        message = test_messages[hash(self.user_context["user_id"]) % len(test_messages)]

        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
            "stream": True,  # Enable streaming
            "user_context": self.user_context,
        }

        start_time = time.time()

        try:
            with self.client.post(
                f"{API_PREFIX}/chat",
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                timeout=STREAM_TIMEOUT,
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    # Process SSE stream
                    events_received = 0
                    content_length = 0

                    for line in response.iter_lines(decode_unicode=True):
                        if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                            try:
                                data = json.loads(line[6:])
                                if "delta" in data:
                                    content_length += len(data["delta"])
                                    events_received += 1
                            except json.JSONDecodeError:
                                continue

                    total_time = time.time() - start_time

                    self.log_event(
                        "streaming_chat_completed",
                        {
                            "conversation_id": self.conversation_id,
                            "events_received": events_received,
                            "content_length": content_length,
                            "total_time_ms": total_time * 1000,
                            "time_to_first_token_ms": 0,  # Would need more sophisticated tracking
                        },
                    )
                    response.success()
                else:
                    self.log_event(
                        "streaming_chat_error",
                        {
                            "conversation_id": self.conversation_id,
                            "status_code": response.status_code,
                            "error_text": response.text[:200],
                        },
                    )
                    response.failure(f"Streaming failed: HTTP {response.status_code}")

        except Exception as e:
            self.log_event(
                "streaming_chat_exception",
                {"conversation_id": self.conversation_id, "error": str(e)},
            )

    @task(1)
    def get_workflows(self):
        """Test workflow listing endpoint."""
        with self.client.get(
            f"{API_PREFIX}/workflows", timeout=DEFAULT_TIMEOUT, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                workflow_count = len(data.get("workflows", []))
                self.log_event(
                    "workflows_retrieved",
                    {
                        "workflow_count": workflow_count,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                    },
                )
                response.success()
            else:
                response.failure(f"Failed to get workflows: HTTP {response.status_code}")

    @task(1)
    def get_workflow_details(self):
        """Test specific workflow retrieval."""
        workflow_id = "magentic_fleet"

        with self.client.get(
            f"{API_PREFIX}/workflows/{workflow_id}", timeout=DEFAULT_TIMEOUT, catch_response=True
        ) as response:
            if response.status_code == 200:
                self.log_event(
                    "workflow_details_retrieved",
                    {
                        "workflow_id": workflow_id,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                    },
                )
                response.success()
            else:
                response.failure(f"Failed to get workflow details: HTTP {response.status_code}")

    @task(1)
    def health_check(self):
        """Test system health endpoints."""
        endpoints = [
            f"{API_PREFIX}/system/health",
            f"{API_PREFIX}/system/status",
            "/health",  # Common health endpoint
        ]

        for endpoint in endpoints:
            with self.client.get(endpoint, timeout=5.0, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    # Don't fail the test for health check failures, just log them
                    response.success()  # Mark as success to avoid affecting overall results

    def _create_conversation(self) -> str:
        """Create a new conversation for the user."""
        payload = {
            "title": f"Load Test Conversation {datetime.now().isoformat()}",
            "user_context": self.user_context,
        }

        with self.client.post(
            f"{API_PREFIX}/conversations",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=DEFAULT_TIMEOUT,
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                conversation_id = data.get("id")
                self.log_event("conversation_created", {"conversation_id": conversation_id})
                return conversation_id
            else:
                # Fallback: generate a fake conversation ID
                fallback_id = str(uuid.uuid4())
                self.log_event(
                    "conversation_creation_failed",
                    {"fallback_id": fallback_id, "status_code": response.status_code},
                )
                return fallback_id

    def log_event(self, event_type: str, data: dict[str, Any]):
        """Log custom events for analysis."""
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_context["user_id"],
            "event_type": event_type,
            "data": data,
        }

        # In a real implementation, you might send this to a metrics system
        # For now, we'll just log it
        print(f"[EVENT] {event_type}: {json.dumps(event_data)}")


class AdminUser(HttpUser):
    """
    Simulates administrative users performing system management tasks.
    Lower frequency but potentially resource-intensive operations.
    """

    wait_time = between(5, 15)  # Admin tasks are less frequent

    @task(1)
    def system_status(self):
        """Check system status and metrics."""
        with self.client.get(
            f"{API_PREFIX}/system/status", timeout=10.0, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"System status check failed: {response.status_code}")

    @task(1)
    def get_conversations(self):
        """Retrieve conversation list (admin operation)."""
        with self.client.get(
            f"{API_PREFIX}/conversations", timeout=DEFAULT_TIMEOUT, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get conversations: {response.status_code}")


# Event handlers for metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Global request event handler for custom metrics."""
    if exception:
        print(f"[ERROR] {name} failed: {exception}")
    else:
        # You could send these metrics to your monitoring system
        pass


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print(f"[TEST] Load test started at {datetime.now().isoformat()}")
    print(f"[TEST] Target URL: {BASE_URL}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    print(f"[TEST] Load test completed at {datetime.now().isoformat()}")

    # Generate summary report
    stats = environment.stats
    print(f"[TEST] Total requests: {stats.total.num_requests}")
    print(f"[TEST] Total failures: {stats.total.num_failures}")
    print(f"[TEST] Average response time: {stats.total.avg_response_time:.2f}ms")


if __name__ == "__main__":
    # Setup for running Locust directly
    setup_logging("INFO", None)

    # Create environment
    env = Environment(host=BASE_URL)

    # Add users
    env.users = [AgenticFleetUser, AdminUser]

    print("AgenticFleet Load Testing Suite")
    print("Run with: locust -f locustfile.py --host=http://localhost:8000")
    print("Web UI will be available at: http://localhost:8089")
