 .PHONY: help install sync clean test test-config test-e2e test-frontend test-automation lint format type-check check run demo-hitl pre-commit-install dev backend frontend-install frontend-dev build-frontend validate-agents load-test-setup load-test-smoke load-test-load load-test-stress load-test-dashboard

# Centralized frontend directory variable to avoid repeating literal path strings.
# Update here if the frontend root moves.
FRONTEND_DIR := src/frontend

# Default target
help:
	@echo "AgenticFleet - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install/sync dependencies (first time or update)"
	@echo "  make dev-setup         Full development setup (install + frontend + pre-commit)"
	@echo "  make sync              Sync dependencies from lockfile"
	@echo "  make frontend-install  Install frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run               Run the main application"
	@echo "  make dev               Run backend + frontend together (full stack)"
	@echo "  make backend           Run backend only (port 8000)"
	@echo "  make frontend-dev      Run frontend only (port 5173)"
	@echo "  make build-frontend    Build frontend for production (outputs to backend/ui)"
	@echo "  make test              Run all tests"
	@echo "  make test-config       Run configuration validation"
	@echo "  make test-e2e          Run end-to-end frontend tests (requires dev running)"
	@echo "  make test-frontend     Run frontend unit tests"
	@echo "  make test-automation   Run automated test suite with quality monitoring"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              Run Ruff linter"
	@echo "  make format            Format code with Ruff (lint + style)"
	@echo "  make type-check        Run mypy type checker"
	@echo "  make check             Run all quality checks (lint + format + type)"
	@echo ""
	@echo "Tools:"
	@echo "  make pre-commit-install  Install pre-commit hooks"
	@echo "  make clean             Remove cache and build artifacts"
	@echo "  make demo-hitl         Run the HITL walkthrough example"
	@echo "  make validate-agents   Validate AGENTS.md invariants"
	@echo ""
	@echo "Load Testing:"
	@echo "  make load-test-setup  Setup load testing environment"
	@echo "  make load-test-smoke  Run smoke test (quick validation)"
	@echo "  make load-test-load   Run normal load test"
	@echo "  make load-test-stress Run stress test"
	@echo "  make load-test-dashboard Start performance dashboard"
	@echo ""

# Setup commands
install:
	GIT_LFS_SKIP_SMUDGE=1 uv sync --pre --all-extras --upgrade
	@echo "✓ Python dependencies installed"
	@echo ""
	@echo "Next: Run 'make frontend-install' to install frontend dependencies"

dev-setup: install frontend-install pre-commit-install
	@echo "✓ Development environment setup complete"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Create .env file: cp .env.example .env"
	@echo "  2. Add your OPENAI_API_KEY to .env"
	@echo "  3. Run 'make dev' to start the application"

sync:
	GIT_LFS_SKIP_SMUDGE=1 uv sync

frontend-install:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install
	@echo "✓ Frontend dependencies installed"

# Run application
run:
	uv run python -m agentic_fleet

# Full stack development (backend + frontend)
dev:
	@echo "Starting AgenticFleet Full Stack Development..."
	@echo ""
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@echo ""
	@bash -c ' \
		trap "kill 0" EXIT INT TERM; \
		uv run uvicorn agentic_fleet.api.main:app --reload --port 8000 --log-level info & \
		sleep 2; \
		cd $(FRONTEND_DIR) && npm run dev & \
		wait'


# DevUI backend server only
backend:
	@echo "Starting minimal backend on http://localhost:8000"
	uv run uvicorn agentic_fleet.api.main:app --reload --port 8000 --log-level info

# Frontend dev server only
frontend-dev:
	@echo "Starting frontend on http://localhost:5173"
	cd $(FRONTEND_DIR) && npm run dev

# Build frontend for production
build-frontend:
	@echo "Building frontend for production..."
	cd $(FRONTEND_DIR) && npm run build
	@echo "✓ Frontend built to src/agentic_fleet/ui"

# Testing
test:
	uv run pytest -v

test-config:
	uv run python -c "from agentic_fleet.utils.factory import WorkflowFactory; factory = WorkflowFactory(); print(f'✓ Loaded {len(factory.list_available_workflows())} workflows from config')"

test-e2e:
	@echo "Running E2E tests (requires backend + frontend running)..."
	cd $(FRONTEND_DIR) && npx playwright test

test-frontend:
	@echo "Running frontend unit tests..."
	cd $(FRONTEND_DIR) && npm test

test-automation:
	@echo "Running automated test suite with quality monitoring..."
	uv run python tests/test_automation.py

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

type-check:
	uv run mypy src

# Run all checks
check: lint type-check
	@echo "✓ All quality checks passed!"

# Validate AGENTS.md invariants
validate-agents:
	uv run python tools/scripts/validate_agents_docs.py --format text

# Pre-commit
pre-commit-install:
	uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned cache directories"

# Load Testing
load-test-setup:
	@echo "🚀 Setting up load testing environment..."
	cd tests/load_testing && ./setup.sh

load-test-smoke:
	@echo "🔍 Running smoke test..."
	@echo "Note: Make sure the backend is running with 'make backend'"
	cd tests/load_testing && python3 run_load_tests.py --scenario smoke_test --health-check

load-test-load:
	@echo "⚡ Running load test..."
	@echo "Note: Make sure the backend is running with 'make backend'"
	cd tests/load_testing && python3 run_load_tests.py --scenario normal_load --health-check

load-test-stress:
	@echo "💪 Running stress test..."
	@echo "Note: Make sure the backend is running with 'make backend'"
	cd tests/load_testing && python3 run_load_tests.py --scenario stress_test --health-check

load-test-dashboard:
	@echo "📊 Starting performance dashboard..."
	cd tests/load_testing && python3 dashboard.py
