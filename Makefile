.PHONY: help install dev-setup sync clean test test-fast test-config test-e2e test-frontend test-all lint format type-check check run pre-commit-install dev backend frontend-install frontend-dev build-frontend analyze-history self-improve init-var clear-cache qa frontend-lint frontend-format evaluate-history tracing-start tracing-stop optimize security docs docs-serve version hooks-install hooks-uninstall hooks-update setup-hooks benchmark diagnostic-server generate-openapi validate-models

# ============================================================================
# Variables
# ============================================================================
FRONTEND_DIR := src/frontend
PYTHON := uv run python
PYTEST := uv run pytest
PYTEST_OPTS := -q --tb=short
PYTEST_PARALLEL := -n auto  # Use all CPU cores

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
CYAN := \033[0;36m
NC := \033[0m  # No Color

# ============================================================================
# Default Target
# ============================================================================
help:
	@echo ""
	@echo "$(CYAN)AgenticFleet - Development Commands$(NC)"
	@echo "======================================"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  install           Install/sync dependencies (first time or update)"
	@echo "  dev-setup         Full development setup (install + frontend + hooks)"
	@echo "  sync              Sync dependencies from lockfile"
	@echo "  frontend-install  Install frontend dependencies"
	@echo "  init-var          Initialize .var/ directory structure"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  dev               Run backend + frontend together (full stack)"
	@echo "  backend           Run backend only (port 8000)"
	@echo "  frontend-dev      Run frontend only (port 5173)"
	@echo "  run               Run CLI application"
	@echo "  build-frontend    Build frontend for production"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  test              Run backend tests"
	@echo "  test-fast         Run backend tests in parallel (faster)"
	@echo "  test-frontend     Run frontend unit tests"
	@echo "  test-all          Run all tests (backend + frontend)"
	@echo "  test-config       Validate workflow configuration"
	@echo "  test-e2e          Run E2E tests (requires dev servers)"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  check             Quick check (lint + type-check)"
	@echo "  qa                Full QA suite (lint + format + type + tests)"
	@echo "  lint              Run Ruff linter"
	@echo "  format            Format code with Ruff"
	@echo "  type-check        Run ty type checker"
	@echo "  frontend-lint     Run ESLint on frontend"
	@echo "  frontend-format   Format frontend with Prettier"
	@echo "  security          Run security scan (bandit)"
	@echo ""
	@echo "$(GREEN)DSPy & Optimization:$(NC)"
	@echo "  optimize          Run GEPA optimization on DSPy modules"
	@echo "  evaluate-history  Evaluate execution history with DSPy"
	@echo "  analyze-history   Analyze workflow execution patterns"
	@echo "  self-improve      Run self-improvement cycle"
	@echo "  clear-cache       Clear compiled DSPy cache"
	@echo ""
	@echo "$(GREEN)Documentation:$(NC)"
	@echo "  docs              Build documentation (requires docs group)"
	@echo "  docs-serve        Serve documentation locally"
	@echo ""
	@echo "$(GREEN)Observability:$(NC)"
	@echo "  tracing-start     Start Jaeger + OTEL collector (port 16686)"
	@echo "  tracing-stop      Stop tracing infrastructure"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  clean             Remove cache and build artifacts"
	@echo "  version           Show current version"
	@echo "  benchmark         Run API performance benchmark"
	@echo "  diagnostic-server Start diagnostic server"
	@echo "  generate-openapi  Generate OpenAPI specification"
	@echo "  validate-models   Validate LiteLLM model configurations"
	@echo "  pre-commit-install Install git pre-commit hooks"
	@echo "  hooks-install     Install enhanced git hooks"
	@echo "  hooks-uninstall   Remove enhanced git hooks"
	@echo "  hooks-update      Update enhanced git hooks"
	@echo "  setup-hooks       Install all hooks (pre-commit + enhanced)"
	@echo ""

# ============================================================================
# Setup Commands
# ============================================================================
install:
	@echo "$(CYAN)Installing dependencies...$(NC)"
	GIT_LFS_SKIP_SMUDGE=1 uv sync --all-extras
	@echo "$(GREEN)✓ Python dependencies installed$(NC)"
	@echo ""
	@echo "Next: Run 'make frontend-install' to install frontend dependencies"

dev-setup: install frontend-install setup-hooks init-var
	@echo ""
	@echo "$(GREEN)✓ Development environment setup complete$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Create .env file: cp .env.example .env"
	@echo "  2. Add your OPENAI_API_KEY to .env"
	@echo "  3. Run 'make dev' to start the application"

sync:
	GIT_LFS_SKIP_SMUDGE=1 uv sync

frontend-install:
	@echo "$(CYAN)Installing frontend dependencies...$(NC)"
	cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

init-var:
	@mkdir -p .var/cache/dspy
	@mkdir -p .var/logs/gepa
	@mkdir -p .var/logs/evaluation
	@mkdir -p .var/data/db
	@mkdir -p .var/checkpoints
	@echo "$(GREEN)✓ Initialized .var/ directory structure$(NC)"

# ============================================================================
# Development Commands
# ============================================================================
run:
	uv run agentic-fleet run

dev:
	@echo "$(CYAN)Starting AgenticFleet Full Stack Development...$(NC)"
	@echo ""
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@echo ""
	@bash -c ' \
		trap "kill 0" EXIT INT TERM; \
		uv run uvicorn agentic_fleet.main:app --reload --port 8000 --log-level info & \
		sleep 2; \
		cd $(FRONTEND_DIR) && npm run dev & \
		wait'

backend:
	@echo "$(CYAN)Starting backend on http://localhost:8000$(NC)"
	uv run uvicorn agentic_fleet.main:app --reload --port 8000 --log-level info

frontend-dev:
	@echo "$(CYAN)Starting frontend on http://localhost:5173$(NC)"
	cd $(FRONTEND_DIR) && npm run dev

build-frontend:
	@echo "$(CYAN)Building frontend for production...$(NC)"
	cd $(FRONTEND_DIR) && npm run build
	@echo "$(GREEN)✓ Frontend built$(NC)"

# ============================================================================
# Testing Commands
# ============================================================================
test:
	$(PYTEST) $(PYTEST_OPTS) tests/

test-fast:
	@echo "$(CYAN)Running tests in parallel...$(NC)"
	$(PYTEST) $(PYTEST_OPTS) $(PYTEST_PARALLEL) tests/

test-frontend:
	@echo "$(CYAN)Running frontend unit tests...$(NC)"
	cd $(FRONTEND_DIR) && npm run test:run

test-all: test test-frontend
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-config:
	@$(PYTHON) -c "from agentic_fleet.utils.cfg import load_config; cfg = load_config(); print(f'$(GREEN)✓ Config valid: {len(cfg.get(\"agents\", {}))} agents$(NC)')"

test-e2e:
	@echo "$(CYAN)Running E2E tests (requires dev servers)...$(NC)"
	cd $(FRONTEND_DIR) && npx playwright test

# ============================================================================
# Code Quality Commands
# ============================================================================
lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

type-check:
	uv run ty check src

frontend-lint:
	cd $(FRONTEND_DIR) && npm run lint

frontend-format:
	cd $(FRONTEND_DIR) && npm run format

security:
	@echo "$(CYAN)Running security scan...$(NC)"
	uv run bandit -r src/agentic_fleet -ll -ii
	@echo "$(GREEN)✓ Security scan complete$(NC)"

check: lint type-check
	@echo "$(GREEN)✓ Quick checks passed$(NC)"

qa: format lint type-check frontend-lint frontend-format test-fast test-frontend
	@echo "$(GREEN)✓ Full QA complete$(NC)"

pre-commit-install:
	uv run pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

# ============================================================================
# Hooks Commands
# ============================================================================
hooks-install:
	@echo "$(CYAN)Installing enhanced git hooks...$(NC)"
	@chmod +x .githooks/*
	@cp .githooks/pre-commit .git/hooks/ 2>/dev/null || true
	@cp .githooks/pre-push .git/hooks/ 2>/dev/null || true
	@cp .githooks/prepare-commit-msg .git/hooks/ 2>/dev/null || true
	@cp .githooks/post-checkout .git/hooks/ 2>/dev/null || true
	@echo "$(GREEN)✓ Enhanced git hooks installed$(NC)"
	@echo "  Available hooks:"
	@echo "  • pre-commit        - Quality checks before commit"
	@echo "  • pre-push          - Validation before push"
	@echo "  • prepare-commit-msg - Auto-prefix commits"
	@echo "  • post-checkout     - Dependency sync on branch switch"

hooks-uninstall:
	@echo "$(CYAN)Removing enhanced git hooks...$(NC)"
	@rm -f .git/hooks/pre-commit .git/hooks/pre-push \
		.git/hooks/prepare-commit-msg .git/hooks/post-checkout
	@echo "$(GREEN)✓ Enhanced git hooks removed$(NC)"

hooks-update:
	$(MAKE) hooks-uninstall
	$(MAKE) hooks-install

setup-hooks: pre-commit-install hooks-install
	@echo "$(GREEN)✓ All hooks setup complete$(NC)"

# ============================================================================
# DSPy & Optimization Commands
# ============================================================================
optimize:
	@echo "$(CYAN)Running GEPA optimization...$(NC)"
	uv run agentic-fleet optimize

evaluate-history:
	@echo "$(CYAN)Evaluating execution history...$(NC)"
	$(PYTHON) scripts/evaluate_history.py

analyze-history:
	@echo "$(CYAN)Analyzing execution patterns...$(NC)"
	$(PYTHON) -m agentic_fleet.scripts.analyze_history

self-improve:
	@echo "$(CYAN)Running self-improvement cycle...$(NC)"
	$(PYTHON) -m agentic_fleet.scripts.self_improve

clear-cache:
	@rm -f .var/logs/compiled_supervisor.pkl .var/logs/compiled_supervisor.pkl.meta
	@rm -rf .var/cache/dspy/*
	@echo "$(GREEN)✓ DSPy cache cleared$(NC)"

# ============================================================================
# Documentation Commands
# ============================================================================
docs:
	@echo "$(CYAN)Building documentation...$(NC)"
	uv run --group docs mkdocs build
	@echo "$(GREEN)✓ Documentation built to site/$(NC)"

docs-serve:
	@echo "$(CYAN)Serving documentation at http://localhost:8080$(NC)"
	uv run --group docs mkdocs serve -a localhost:8080

# ============================================================================
# Observability Commands
# ============================================================================
tracing-start:
	@echo "$(CYAN)Starting tracing infrastructure...$(NC)"
	@bash scripts/start_tracing.sh
	@echo ""
	@echo "  Jaeger UI: http://localhost:16686"

tracing-stop:
	@bash scripts/stop_tracing.sh
	@echo "$(GREEN)✓ Tracing stopped$(NC)"

# ============================================================================
# Utility Commands
# ============================================================================
version:
	@$(PYTHON) -c "from agentic_fleet import __version__; print(f'AgenticFleet v{__version__}')"

benchmark:
	@echo "$(CYAN)Running API benchmark...$(NC)"
	$(PYTHON) scripts/benchmark_api.py

diagnostic-server:
	@echo "$(CYAN)Starting diagnostic server...$(NC)"
	$(PYTHON) scripts/diagnostic_server.py

generate-openapi:
	@echo "$(CYAN)Generating OpenAPI spec...$(NC)"
	$(PYTHON) scripts/generate_openapi.py

validate-models:
	@echo "$(CYAN)Validating LiteLLM models...$(NC)"
	@bash scripts/validate_litellm_models.sh

clean:
	@echo "$(CYAN)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ site/
	@echo "$(GREEN)✓ Cleaned$(NC)"
