# Plan: Refactor and Stabilize Core Orchestration

## Phase 1: Legacy Code Removal and Cleanup
- [x] Task: Remove `utils/agent_framework_shims.py` and fix immediate import errors. [ef4728b]
    - [ ] Subtask: Delete the file.
    - [ ] Subtask: Scan codebase for imports and replace/remove them.
    - [ ] Subtask: Verify project builds.
- [ ] Task: Clean up deprecated `utils/agent_framework/` directory.
    - [ ] Subtask: Identify unused modules in `src/agentic_fleet/utils/agent_framework/`.
    - [ ] Subtask: Delete confirmed deprecated files.
    - [ ] Subtask: Update `src/agentic_fleet/utils/__init__.py` exports.
- [ ] Task: Conductor - User Manual Verification 'Legacy Code Removal and Cleanup' (Protocol in workflow.md)

## Phase 2: DSPy Module Consolidation
- [ ] Task: Refactor `dspy_modules` to unify reasoning logic.
    - [ ] Subtask: Analyze `reasoner.py` and `reasoner_predictions.py` for overlap.
    - [ ] Subtask: Create a consolidated `DSPyReasoner` class structure.
    - [ ] Subtask: Update unit tests for the reasoner.
- [ ] Task: Audit and Update DSPy Signatures.
    - [ ] Subtask: Review `signatures.py` for Pydantic v2 compliance.
    - [ ] Subtask: Ensure all outputs are strictly typed.
- [ ] Task: Conductor - User Manual Verification 'DSPy Module Consolidation' (Protocol in workflow.md)

## Phase 3: Executor Standardization
- [ ] Task: Standardize Executor Interfaces.
    - [ ] Subtask: Define a strict `BaseExecutor` protocol/abstract base class if missing.
    - [ ] Subtask: Refactor `AnalysisExecutor` and `RoutingExecutor` to match.
    - [ ] Subtask: Refactor `ExecutionExecutor`, `ProgressExecutor`, and `QualityExecutor`.
- [ ] Task: Update Supervisor Workflow integration.
    - [ ] Subtask: Verify `workflows/supervisor.py` uses the standardized executors correctly.
    - [ ] Subtask: Run integration tests for the full pipeline.
- [ ] Task: Conductor - User Manual Verification 'Executor Standardization' (Protocol in workflow.md)

## Phase 4: Final Verification and Testing
- [ ] Task: Run comprehensive type checks.
    - [ ] Subtask: Execute static analysis (mypy/pyright).
    - [ ] Subtask: Fix type errors resulting from refactoring.
- [ ] Task: Execute full test suite.
    - [ ] Subtask: Run `pytest` with coverage.
    - [ ] Subtask: Address any regression failures.
- [ ] Task: Conductor - User Manual Verification 'Final Verification and Testing' (Protocol in workflow.md)
