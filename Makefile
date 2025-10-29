.PHONY: help install sync clean test test-config test-e2e lint format type-check check run demo-hitl pre-commit-install dev backend frontend-install frontend-dev validate-agents

# Default target
help:
	@echo "AgenticFleet - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install dependencies (first time setup)"
	@echo "  make sync              Sync dependencies from lockfile"
	@echo "  make frontend-install  Install frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run               Run the main application"
	@echo "  make dev               Run backend + frontend together (full stack)"
	@echo "  make backend           Run backend only (port 8000)"
	@echo "  make frontend-dev      Run frontend only (port 5173)"
	@echo "  make test              Run all tests"
	@echo "  make test-config       Run configuration validation"
	@echo "  make test-e2e          Run end-to-end frontend tests (requires dev running)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              Run Ruff linter"
	@echo "  make format            Format code with Black and Ruff"
	@echo "  make type-check        Run mypy type checker"
	@echo "  make check             Run all quality checks (lint + format + type)"
	@echo ""
	@echo "Tools:"
	@echo "  make pre-commit-install  Install pre-commit hooks"
	@echo "  make clean             Remove cache and build artifacts"
	@echo "  make demo-hitl         Run the HITL walkthrough example"
	@echo "  make validate-agents   Validate AGENTS.md invariants"
	@echo ""

# Setup commands
install:
	uv pip install agentic-fleet[all] --pre -U
	@echo "✓ Python dependencies installed"
	@echo ""
	@echo "Next: Run 'make frontend-install' to install frontend dependencies"

sync:
	uv sync

frontend-install:
	@echo "Installing frontend dependencies..."
	cd src/frontend && npm install
	@echo "✓ Frontend dependencies installed"

# Run application
run:
	uv run python -m agenticfleet

# Full stack development (backend + frontend)
dev:
	@echo "Starting AgenticFleet Full Stack Development..."
	@echo ""
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@echo ""
	@trap 'kill 0' INT; \
	uv run uvicorn agenticfleet.server:app --reload --port 8000 & \
	cd src/frontend && npm run dev


# DevUI backend server only
backend:
	@echo "Starting minimal backend on http://localhost:8000"
	uv run uvicorn agenticfleet.server:app --reload --port 8000

# Frontend dev server only
frontend-dev:
	@echo "Starting frontend on http://localhost:5173"
	cd src/frontend && npm run dev

# Testing
test:
	uv run pytest -v

test-config:
	uv run python tests/test_config.py

test-e2e:
	@echo "Running E2E tests (requires backend + frontend running)..."
	uv run python tests/e2e/playwright_test_workflow.py

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run black .

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
