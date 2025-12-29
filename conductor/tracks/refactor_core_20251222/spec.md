# Specification: Refactor and Stabilize Core Orchestration

## Goal

To modernize and stabilize the AgenticFleet backend by removing technical debt, consolidating DSPy reasoning modules, and finalizing the migration to the executor-based architecture compatible with Microsoft Agent Framework v1.0.

## Core Requirements

### 1. Legacy Cleanup

- **Remove `utils/agent_framework_shims.py`**: Eliminate temporary compatibility layers.
- **Clean up `utils/agent_framework/`**: Remove deprecated utility modules replaced by the new architecture.
- **Audit Imports**: Ensure no code relies on removed legacy modules.

### 2. DSPy Consolidation

- **Unify Reasoner Logic**: Merge scattered reasoning logic from `dspy_modules/reasoner.py` and `dspy_modules/reasoner_predictions.py` where appropriate.
- **Update Signatures**: Ensure all DSPy signatures in `dspy_modules/signatures.py` use Pydantic v2 models for strict validation.
- **Optimize Compilation**: Verify that the DSPy compiler integration (`utils/compiler.py`) is correctly targeting the new signatures.

### 3. Executor Architecture Finalization

- **Standardize Executors**: Ensure `AnalysisExecutor`, `RoutingExecutor`, `ExecutionExecutor`, `ProgressExecutor`, and `QualityExecutor` share a consistent interface and error handling strategy.
- **Verify `SupervisorWorkflow`**: Confirm that the main supervisor workflow correctly orchestrates these executors without bypassing logic.

### 4. Compatibility Verification

- **Agent Framework v1.0**: Validate that all agent interactions comply with the stable v1.0 API of `azure-ai-agents` and `agent-framework`.
- **Type Safety**: Run `mypy` or `pyright` to ensure strict typing across the refactored modules.

## Success Criteria

- [ ] All legacy shim files are deleted.
- [ ] The codebase passes `ruff check .` and `mypy .` (or equivalent type check).
- [ ] The test suite (`tests/`) passes with >80% coverage.
- [ ] No `DeprecationWarning` related to internal framework usage during runtime.
