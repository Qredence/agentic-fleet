 .PHONY: help install dev-setup sync clean test test-config test-e2e test-frontend test-all lint format type-check check run pre-commit-install dev backend frontend-install frontend-dev build-frontend analyze-history self-improve init-var clear-cache qa frontend-lint frontend-format evaluate-history tracing-start tracing-stop

# Centralized variables
FRONTEND_DIR := src/frontend
PYTHON := uv run python
PYTEST := uv run pytest
PYTEST_OPTS := -q --tb=short

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
	@echo ""
	@echo "Testing:"
	@echo "  make test              Run backend tests (fast)"
	@echo "  make test-frontend     Run frontend unit tests"
	@echo "  make test-all          Run all tests (backend + frontend)"
	@echo "  make test-config       Run configuration validation"
	@echo "  make test-e2e          Run end-to-end tests (requires dev running)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              Run Ruff linter (backend)"
	@echo "  make format            Format code with Ruff (backend)"
	@echo "  make frontend-lint     Run ESLint (frontend)"
	@echo "  make frontend-format   Format code with Prettier (frontend)"
	@echo "  make type-check        Run ty type checker"
	@echo "  make check             Quick quality check (lint + type-check)"
	@echo "  make qa                Full QA suite (lint + format + type + all tests)"
	@echo ""
	@echo "Tools:"
	@echo "  make pre-commit-install  Install pre-commit hooks"
	@echo "  make clean             Remove cache and build artifacts"
	@echo "  make init-var          Initialize .var/ directory structure"
	@echo "  make clear-cache       Clear compiled DSPy cache"
	@echo "  make analyze-history   Analyze workflow execution history"
	@echo "  make evaluate-history  Run DSPy-based evaluation on execution history"
	@echo "  make self-improve      Run self-improvement analysis"
	@echo ""
	@echo "Tracing & Visualization (OpenTelemetry):"
	@echo "  make tracing-start     Start OpenTelemetry collector + Jaeger UI (port 16686)"
	@echo "  make tracing-stop      Stop the tracing collector"
	@echo ""

# Setup commands
install:
	GIT_LFS_SKIP_SMUDGE=1 uv sync --all-extras
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
		uv run uvicorn agentic_fleet.main:app --reload --port 8000 --log-level info & \
		sleep 2; \
		cd $(FRONTEND_DIR) && npm run dev & \
		wait'


# DevUI backend server only
backend:
	@echo "Starting minimal backend on http://localhost:8000"
	uv run uvicorn agentic_fleet.main:app --reload --port 8000 --log-level info

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
	$(PYTEST) $(PYTEST_OPTS) tests/

test-frontend:
	@echo "Running frontend unit tests..."
	cd $(FRONTEND_DIR) && npm run test:run

test-all: test test-frontend
	@echo "✓ All tests passed (backend + frontend)"

test-config:
	$(PYTHON) -c "from agentic_fleet.utils.cfg import load_config; cfg = load_config(); agent_count = len(cfg.get('agents', {})); print(f'✓ Loaded workflow_config.yaml ({agent_count} agents)')"

test-e2e:
	@echo "Running E2E tests (requires backend + frontend running)..."
	cd $(FRONTEND_DIR) && npx playwright test

# Code quality
lint:
	uv run ruff check .

frontend-lint:
	@echo "Running frontend linter..."
	cd $(FRONTEND_DIR) && npm run lint

format:
	uv run ruff check --fix .
	uv run ruff format .

frontend-format:
	@echo "Formatting frontend code..."
	cd $(FRONTEND_DIR) && npm run format

type-check:
	uv run ty check src

# Quick quality check (fast, no tests)
check: lint type-check
	@echo "✓ Quick quality checks passed!"

# Full QA suite (comprehensive)
qa: lint format type-check frontend-lint test-all
	@echo "✓ Full QA complete: All checks passed!"

# Pre-commit
pre-commit-install:
	uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Analysis tools
analyze-history:
	@echo "Analyzing workflow execution history..."
	$(PYTHON) -m agentic_fleet.scripts.analyze_history

evaluate-history:
	@echo "Running DSPy-based evaluation on execution history..."
	$(PYTHON) scripts/evaluate_history.py

self-improve:
	@echo "Running self-improvement analysis..."
	$(PYTHON) -m agentic_fleet.scripts.self_improve

# Initialize .var/ directory structure for runtime data
init-var:
	@mkdir -p .var/cache/dspy
	@mkdir -p .var/logs/gepa
	@mkdir -p .var/logs/evaluation
	@mkdir -p .var/data/db
	@echo "✓ Initialized .var/ directory structure"

# Clear compiled DSPy cache
clear-cache:
	@rm -f .var/logs/compiled_supervisor.pkl .var/logs/compiled_supervisor.pkl.meta
	@echo "✓ Cleared compiled DSPy cache"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned cache directories"
# Tracing & Visualization
tracing-start:
	@bash scripts/start_tracing.sh

tracing-stop:
	@bash scripts/stop_tracing.sh
