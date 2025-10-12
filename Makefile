.PHONY: help install sync clean test test-config lint format type-check check run pre-commit-install

# Default target
help:
	@echo "AgenticFleet - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install dependencies (first time setup)"
	@echo "  make sync              Sync dependencies from lockfile"
	@echo ""
	@echo "Development:"
	@echo "  make run               Run the main application"
	@echo "  make test              Run all tests"
	@echo "  make test-config       Run configuration validation"
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
	@echo ""

# Setup commands
install:
	uv sync --all-extras

sync:
	uv sync

# Run application
run:
	uv run python -m agenticfleet

# Testing
test:
	uv run pytest -v

test-config:
	uv run python tests/test_config.py

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run black .

type-check:
	uv run mypy .

# Run all checks
check: lint type-check
	@echo "✓ All quality checks passed!"

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
