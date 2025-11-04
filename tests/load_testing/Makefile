# AgenticFleet Load Testing Makefile

.PHONY: help setup test-smoke test-load test-stress test-k6 clean reports monitor

# Default target
help:
	@echo "AgenticFleet Load Testing Commands:"
	@echo ""
	@echo "  setup          - Setup the load testing environment"
	@echo "  test-smoke     - Run smoke test (quick validation)"
	@echo "  test-load      - Run normal load test"
	@echo "  test-stress    - Run stress test"
	@echo "  test-k6        - Run k6 load test"
	@echo "  test-spike     - Run spike test"
	@echo "  test-endurance - Run endurance test"
	@echo "  monitor        - Start monitoring server"
	@echo "  reports        - Generate performance reports"
	@echo "  clean          - Clean up test artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make test-smoke"
	@echo "  make test-load USERS=100 DURATION=10m"
	@echo "  make test-k6 VUS=50"

# Configuration
USERS ?= 50
SPAWN_RATE ?= 5
DURATION ?= 5m
HOST ?= http://localhost:8000
ENVIRONMENT ?= local

# Setup
setup:
	@echo "🚀 Setting up load testing environment..."
	./setup.sh

# Test targets
test-smoke:
	@echo "🔍 Running smoke test..."
	python3 run_load_tests.py --scenario smoke_test --environment $(ENVIRONMENT) --host $(HOST) --health-check

test-load:
	@echo "⚡ Running load test..."
	python3 run_load_tests.py --tool locust --users $(USERS) --spawn-rate $(SPAWN_RATE) --duration $(DURATION) --environment $(ENVIRONMENT) --host $(HOST) --health-check

test-stress:
	@echo "💪 Running stress test..."
	python3 run_load_tests.py --scenario stress_test --environment $(ENVIRONMENT) --host $(HOST) --health-check

test-spike:
	@echo "📈 Running spike test..."
	python3 run_load_tests.py --scenario spike_test --environment $(ENVIRONMENT) --host $(HOST) --health-check

test-endurance:
	@echo "⏰ Running endurance test..."
	python3 run_load_tests.py --scenario endurance_test --environment $(ENVIRONMENT) --host $(HOST) --health-check

test-k6:
	@echo "🚀 Running k6 test..."
	BASE_URL=$(HOST) VUS=$(USERS) python3 run_load_tests.py --tool k6

# Test with web UI (interactive)
test-ui:
	@echo "🖥️  Starting Locust web UI..."
	locust -f locustfile.py --host $(HOST) --web-host 0.0.0.0 --web-port 8089

# Monitoring
monitor:
	@echo "📊 Starting monitoring server..."
	python3 -c "
import asyncio
from monitoring import create_test_run_info, run_monitoring_session

test_info = create_test_run_info(
    'monitoring_session', '$(ENVIRONMENT)', '$(HOST)', 0, 'monitoring'
)

asyncio.run(run_monitoring_session(test_info, 60))
"

# Reports
reports:
	@echo "📋 Generating reports..."
	@if [ -d "reports" ]; then \
		echo "Available reports:"; \
		ls -la reports/; \
	else \
		echo "No reports directory found. Run tests first."; \
	fi

# Clean
clean:
	@echo "🧹 Cleaning up test artifacts..."
	rm -rf reports/* logs/* data/*
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.log" -delete
	@echo "✅ Cleanup completed"

# Health check
health-check:
	@echo "🏥 Running health check..."
	python3 run_load_tests.py --health-check --environment $(ENVIRONMENT) --host $(HOST)

# List scenarios
list-scenarios:
	@echo "📋 Available test scenarios:"
	python3 run_load_tests.py --list-scenarios

# Performance analysis
analyze:
	@echo "📊 Analyzing performance data..."
	@if [ -f "reports/*_metrics.json" ]; then \
		python3 -c "
import json
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Load latest metrics
metrics_files = glob.glob('reports/*_metrics.json')
if metrics_files:
    latest_file = max(metrics_files)
    with open(latest_file) as f:
        data = json.load(f)

    print(f'Analyzing: {latest_file}')
    print('Summary:')
    print(json.dumps(data['summary'], indent=2))
else:
    print('No metrics files found. Run tests first.')
	"; \
	else \
		echo "No metrics files found. Run tests first."; \
	fi

# Installation checks
check-deps:
	@echo "🔍 Checking dependencies..."
	@echo "Python version: $(shell python3 --version)"
	@echo "Locust: $(shell python3 -c 'import locust; print(locust.__version__)' 2>/dev/null || echo 'Not installed')"
	@echo "k6: $(shell k6 version 2>/dev/null || echo 'Not installed')"
	@echo "Prometheus client: $(shell python3 -c 'import prometheus_client; print(prometheus_client.__version__)' 2>/dev/null || echo 'Not installed')"

# Development targets
dev-setup: setup check-deps
	@echo "🛠️  Development setup completed!"

# Quick test (for CI/CD)
quick-test:
	@echo "⚡ Running quick test..."
	python3 run_load_tests.py --scenario smoke_test --environment $(ENVIRONMENT) --host $(HOST) --health-check --timeout 60

# Comprehensive test suite
test-all: test-smoke test-load test-k6
	@echo "✅ All tests completed!"
	@echo "📊 Check reports/ directory for results"

# Docker targets (if needed)
docker-build:
	@echo "🐳 Building Docker image for load testing..."
	docker build -t agentic-fleet-load-test .

docker-test:
	@echo "🐳 Running tests in Docker..."
	docker run --rm -it --network host agentic-fleet-load-test make test-smoke HOST=$(HOST)

# Help for specific tools
help-locust:
	@echo "📚 Locust Documentation:"
	@echo "Web UI: http://localhost:8089"
	@echo "Command line: locust -f locustfile.py --host $(HOST) --headless"
	@echo "Custom options: locust --help"

help-k6:
	@echo "📚 k6 Documentation:"
	@echo "Basic usage: k6 run k6-chat-test.js"
	@echo "With environment: BASE_URL=$(HOST) k6 run k6-chat-test.js"
	@echo "Custom options: k6 run --help"
