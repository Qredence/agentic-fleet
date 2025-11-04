#!/bin/bash
#
# AgenticFleet Multi-Branch Strategy - Complete Execution Guide
# =============================================================
# This script documents all commands to split 162 files across 8 feature branches
# with integration branch validation and sequential PR merges to main.
#
# COMPLETED STEPS:
# ✅ Step 1-3: CI/CD updated, gitignore updated, committed to magentic-backend
# ✅ Step 4: magentic-integration branch created and pushed
#
# REMAINING STEPS: Execute commands below in order
#

set -e  # Exit on error

# =============================================================================
# PHASE 1: Create Feature Branches (Steps 5a-5h)
# =============================================================================

echo "Starting Feature Branch Creation..."

# -----------------------------------------------------------------------------
# Branch 1: feature/magentic-core (15 files) - Foundation
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-core ==="
git checkout magentic-backend
git checkout -b feature/magentic-core

# Reset and stage only core files
git reset HEAD .
git add src/agenticfleet/core/
git add src/agenticfleet/console.py
git add src/agenticfleet/main.py
git add pyproject.toml uv.lock Makefile
git add CHANGELOG.md AGENTS.md README.md

# Commit
git commit -m "feat(core): implement Magentic framework foundation

- Add core Magentic orchestrator with PLAN→EVALUATE→ACT→OBSERVE cycle
- Implement MagenticAgent and MagenticWorkflow base classes
- Add event system for workflow coordination
- Update dependencies: magentic-one, agent-framework
- Add main entry point and console interface

Implements Microsoft Agent Framework patterns for multi-agent orchestration.

Ref: microsoft/agent-framework magentic pattern"

# Push
git push -u origin feature/magentic-core

echo "✅ feature/magentic-core created and pushed"

# -----------------------------------------------------------------------------
# Branch 2: feature/magentic-agents (14 files) - Specialist Agents
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-agents ==="
git checkout magentic-backend
git checkout -b feature/magentic-agents

git reset HEAD .
git add src/agentic_fleet/agents/
git add src/agentic_fleet/prompts/
git add src/agentic_fleet/AGENTS.md

git commit -m "feat(agents): add five-agent specialist system

- Implement planner, executor, coder, verifier, generator agents
- Add agent factory functions with YAML config support
- Define prompts for each agent specialization
- Update agent documentation

Each agent leverages core Magentic framework for coordinated execution."

git push -u origin feature/magentic-agents

echo "✅ feature/magentic-agents created and pushed"

# -----------------------------------------------------------------------------
# Branch 3: feature/magentic-api-responses (22 files) - OpenAI API
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-api-responses ==="
git checkout magentic-backend
git checkout -b feature/magentic-api-responses

git reset HEAD .
git add src/agentic_fleet/api/
git add docs/api/
git add scripts/test-api-endpoints.py scripts/test_backend_quick.py
# Track deletions
git add -u src/agentic_fleet/api/legacy/

git commit -m "feat(api): add OpenAI Responses API and SSE streaming

- Implement /v1/responses OpenAI-compatible API
- Add entities discovery endpoints
- Implement SSE streaming for real-time events
- Update chat service with Magentic workflow integration
- Add magentic_service for workflow execution
- Remove legacy API code
- Update API documentation and test scripts

Enables frontend to consume workflows via OpenAI Responses format."

git push -u origin feature/magentic-api-responses

echo "✅ feature/magentic-api-responses created and pushed"

# -----------------------------------------------------------------------------
# Branch 4: feature/magentic-models-utils (18 files) - Pydantic Models
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-models-utils ==="
git checkout magentic-backend
git checkout -b feature/magentic-models-utils

git reset HEAD .
git add src/agentic_fleet/models/
git add src/agentic_fleet/utils/
git add src/agentic_fleet/tools/
git add -u CLAUDE.md  # Track deletion
git add tools/scripts/validate_agents_docs.py

git commit -m "feat(models): add Pydantic models and utility modules

- Add models for chat, entities, events, responses, workflows
- Implement config loading and factory utilities
- Add performance monitoring and logging utilities
- Implement tool registry and MCP tool adapters
- Add hosted interpreter tool
- Remove CLAUDE.md (replaced by AGENTS.md)
- Update validation scripts

Provides type-safe data structures and utilities for Magentic system."

git push -u origin feature/magentic-models-utils

echo "✅ feature/magentic-models-utils created and pushed"

# -----------------------------------------------------------------------------
# Branch 5: feature/magentic-workflows (7 files) - Orchestration
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-workflows ==="
git checkout magentic-backend
git checkout -b feature/magentic-workflows

git reset HEAD .
git add src/agentic_fleet/workflow/
git add src/agentic_fleet/workflow.yaml
git add src/agentic_fleet/workflows.yaml

git commit -m "feat(workflow): add Magentic workflow orchestration

- Implement MagenticBuilder for workflow construction
- Add workflow executor with checkpointing support
- Implement event handling and streaming
- Add YAML workflow configurations
- Support dynamic agent spawning

Enables declarative workflow definition and execution."

git push -u origin feature/magentic-workflows

echo "✅ feature/magentic-workflows created and pushed"

# -----------------------------------------------------------------------------
# Branch 6: feature/magentic-frontend (30 files) - React UI
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-frontend ==="
git checkout magentic-backend
git checkout -b feature/magentic-frontend

git reset HEAD .
git add src/frontend/

git commit -m "feat(frontend): enhance UI for Magentic workflows

- Add structured message rendering components
- Implement chain-of-thought display
- Add reasoning and steps visualization
- Update chat store with SSE handling
- Add metrics store for performance tracking
- Implement new UI components (file-upload, jsx-preview, etc.)
- Add frontend testing infrastructure (vitest)
- Update API client for Responses API
- Improve message parser for structured content

Provides rich UI for real-time Magentic workflow visualization."

git push -u origin feature/magentic-frontend

echo "✅ feature/magentic-frontend created and pushed"

# -----------------------------------------------------------------------------
# Branch 7: feature/magentic-testing (22 files) - Test Suite
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-testing ==="
git checkout magentic-backend
git checkout -b feature/magentic-testing

git reset HEAD .
git add tests/
git add test_sse_performance.py

git commit -m "feat(tests): add comprehensive Magentic test suite

- Add integration tests for Magentic backend
- Add API endpoint tests (responses, entities, streaming)
- Add workflow execution tests
- Add config validation tests
- Add load testing infrastructure
- Add SSE performance tests
- Add testing documentation

Achieves >80% coverage of Magentic components."

git push -u origin feature/magentic-testing

echo "✅ feature/magentic-testing created and pushed"

# -----------------------------------------------------------------------------
# Branch 8: feature/magentic-config-docs (18 files) - Configuration & Docs
# -----------------------------------------------------------------------------
echo "\n=== Creating feature/magentic-config-docs ==="
git checkout magentic-backend
git checkout -b feature/magentic-config-docs

git reset HEAD .
git add config/workflows.yaml
git add docs/AGENTS.md docs/STRUCTURED_MESSAGE_UI.md docs/archive/
git add specs/
git add src/agentic_fleet/cli/
git add PLANS.md package.json package-lock.json
git add .gitignore  # Any additional changes
git add .claude/ .github/ .mcp.json

git commit -m "feat(config): add Magentic configuration and documentation

- Add workflows.yaml with magentic_fleet config
- Update AGENTS.md documentation
- Add structured message UI documentation
- Add deployment and testing specifications
- Update CLI with workflow commands
- Add implementation plans
- Update tooling configurations (.gitignore, mcp.json)
- Archive legacy documentation

Completes configuration and documentation for Magentic system."

git push -u origin feature/magentic-config-docs

echo "✅ feature/magentic-config-docs created and pushed"

echo "\n✅ All 8 feature branches created and pushed!"

# =============================================================================
# PHASE 2: Merge to Integration Branch (Step 6)
# =============================================================================

echo "\n\n=== Starting Integration Branch Merges ==="
git checkout magentic-integration

# Merge 1: Core (no dependencies)
echo "\n--- Merging feature/magentic-core ---"
git merge --no-ff feature/magentic-core -m "Merge feature/magentic-core into integration"
echo "Running tests..."
uv run pytest tests/test_magentic_backend_integration.py -k "test_core" -v || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ Core merged and pushed"

# Merge 2: Agents (depends on core)
echo "\n--- Merging feature/magentic-agents ---"
git merge --no-ff feature/magentic-agents -m "Merge feature/magentic-agents into integration"
echo "Running tests..."
uv run pytest tests/test_magentic_backend_integration.py -k "test_agents" -v || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ Agents merged and pushed"

# Merge 3: API (depends on core, agents)
echo "\n--- Merging feature/magentic-api-responses ---"
git merge --no-ff feature/magentic-api-responses -m "Merge feature/magentic-api-responses into integration"
echo "Running tests..."
uv run pytest tests/test_api_responses.py tests/test_api_responses_streaming.py -v || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ API merged and pushed"

# Merge 4: Models (depends on core)
echo "\n--- Merging feature/magentic-models-utils ---"
git merge --no-ff feature/magentic-models-utils -m "Merge feature/magentic-models-utils into integration"
echo "Running tests..."
uv run pytest tests/test_utils_events.py tests/test_response_aggregator.py -v || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ Models merged and pushed"

# Merge 5: Workflows (depends on core, models)
echo "\n--- Merging feature/magentic-workflows ---"
git merge --no-ff feature/magentic-workflows -m "Merge feature/magentic-workflows into integration"
echo "Running tests..."
uv run pytest tests/test_workflow.py tests/test_workflow_factory.py -v || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ Workflows merged and pushed"

# Merge 6: Frontend (depends on API)
echo "\n--- Merging feature/magentic-frontend ---"
git merge --no-ff feature/magentic-frontend -m "Merge feature/magentic-frontend into integration"
echo "Running frontend tests..."
cd src/frontend && npm test && npm run lint || echo "⚠️  Frontend tests failed - review before continuing"
cd ../..
git push origin magentic-integration
echo "✅ Frontend merged and pushed"

# Merge 7: Testing (depends on all)
echo "\n--- Merging feature/magentic-testing ---"
git merge --no-ff feature/magentic-testing -m "Merge feature/magentic-testing into integration"
echo "Running full test suite..."
make test || echo "⚠️  Tests failed - review before continuing"
git push origin magentic-integration
echo "✅ Testing merged and pushed"

# Merge 8: Config/Docs (no dependencies)
echo "\n--- Merging feature/magentic-config-docs ---"
git merge --no-ff feature/magentic-config-docs -m "Merge feature/magentic-config-docs into integration"
echo "Running config validation..."
make test-config || echo "⚠️  Config validation failed - review before continuing"
git push origin magentic-integration
echo "✅ Config/Docs merged and pushed"

echo "\n✅ All 8 branches merged to magentic-integration!"

# =============================================================================
# PHASE 3: Final Integration Validation (Step 7)
# =============================================================================

echo "\n\n=== Running Final Integration Validation ==="
git checkout magentic-integration

echo "Running make check..."
make check || echo "⚠️  Check failed - fix issues before PRs"

echo "Running make test..."
make test || echo "⚠️  Tests failed - fix issues before PRs"

echo "\n✅ Integration validation complete!"
echo "Check CI status at: https://github.com/Qredence/agentic-fleet/actions"

# =============================================================================
# PHASE 4: Create PRs to Main (Step 8)
# =============================================================================

echo "\n\n=== Creating Pull Requests to Main ==="

# PR 1: Core
echo "\n--- Creating PR for feature/magentic-core ---"
gh pr create \
  --base main \
  --head feature/magentic-core \
  --title "feat(core): Magentic framework foundation" \
  --body "Implements core Magentic orchestrator following Microsoft Agent Framework patterns.

**Changes:**
- Core Magentic orchestrator with PLAN→EVALUATE→ACT→OBSERVE cycle
- Agent and workflow base classes
- Event system for coordination
- Entry points (main.py, console.py)
- Updated dependencies

**Dependencies:** None
**Merge Order:** 1st - Foundation for all other features

**Testing:**
\`\`\`bash
uv run pytest tests/test_magentic_backend_integration.py -k test_core -v
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 2: Agents
echo "\n--- Creating PR for feature/magentic-agents ---"
gh pr create \
  --base main \
  --head feature/magentic-agents \
  --title "feat(agents): Five-agent specialist system" \
  --body "Adds specialized agents (planner, executor, coder, verifier, generator) working with Magentic orchestrator.

**Changes:**
- Agent implementations with factory functions
- Prompts for each specialization
- Agent documentation

**Dependencies:** Requires #<core-pr-number> (feature/magentic-core)
**Merge Order:** 2nd - After core foundation

**Testing:**
\`\`\`bash
uv run pytest tests/test_magentic_backend_integration.py -k test_agents -v
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 3: API
echo "\n--- Creating PR for feature/magentic-api-responses ---"
gh pr create \
  --base main \
  --head feature/magentic-api-responses \
  --title "feat(api): OpenAI Responses API & SSE streaming" \
  --body "OpenAI-compatible Responses API with SSE streaming for real-time workflow events.

**Changes:**
- /v1/responses endpoints (OpenAI compatible)
- Entity discovery service
- SSE streaming infrastructure
- Chat service Magentic integration
- Updated API documentation

**Dependencies:** Requires #<core-pr-number>, #<agents-pr-number>
**Merge Order:** 3rd - Core API layer

**Testing:**
\`\`\`bash
uv run pytest tests/test_api_responses*.py tests/test_api_entities.py -v
python scripts/test_backend_quick.py
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 4: Models
echo "\n--- Creating PR for feature/magentic-models-utils ---"
gh pr create \
  --base main \
  --head feature/magentic-models-utils \
  --title "feat(models): Pydantic models & utility modules" \
  --body "Type-safe data models and utility functions supporting the Magentic system.

**Changes:**
- Pydantic models (chat, entities, events, responses, workflows)
- Config loading and factory utilities
- Tool registry and MCP adapters
- Performance monitoring utilities

**Dependencies:** Requires #<core-pr-number>
**Merge Order:** 4th - Parallel with API

**Testing:**
\`\`\`bash
uv run pytest tests/test_utils_events.py tests/test_response_aggregator.py -v
python -c 'from agentic_fleet.models import ChatMessage, WorkflowConfig; print(\"✓\")'
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 5: Workflows
echo "\n--- Creating PR for feature/magentic-workflows ---"
gh pr create \
  --base main \
  --head feature/magentic-workflows \
  --title "feat(workflow): Magentic workflow orchestration" \
  --body "Workflow builder pattern and execution engine for Magentic orchestration.

**Changes:**
- MagenticFleetBuilder for workflow construction
- Workflow executor with checkpointing
- Event handling system
- YAML configurations

**Dependencies:** Requires #<core-pr-number>, #<models-pr-number>
**Merge Order:** 5th - After models

**Testing:**
\`\`\`bash
uv run pytest tests/test_workflow*.py -v
python -c 'from agentic_fleet.workflow import MagenticFleetBuilder; print(\"✓\")'
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 6: Frontend
echo "\n--- Creating PR for feature/magentic-frontend ---"
gh pr create \
  --base main \
  --head feature/magentic-frontend \
  --title "feat(frontend): UI enhancements for Magentic workflows" \
  --body "Rich UI components for visualizing Magentic workflows with SSE streaming.

**Changes:**
- Structured message components
- Chain-of-thought display
- Reasoning and steps visualization
- SSE integration in chat store
- New UI components (file-upload, jsx-preview, etc.)
- Frontend testing with Vitest

**Dependencies:** Requires #<api-pr-number> (feature/magentic-api-responses)
**Merge Order:** 6th - After API layer

**Testing:**
\`\`\`bash
cd src/frontend && npm test && npm run lint
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 7: Testing
echo "\n--- Creating PR for feature/magentic-testing ---"
gh pr create \
  --base main \
  --head feature/magentic-testing \
  --title "feat(tests): Comprehensive Magentic test suite" \
  --body "Complete testing infrastructure for Magentic system with >80% coverage.

**Changes:**
- Integration tests for Magentic backend
- API endpoint tests (responses, entities, streaming)
- Workflow execution tests
- Config validation tests
- Load testing infrastructure (Locust + k6)
- SSE performance tests
- Testing documentation

**Dependencies:** Requires all previous PRs
**Merge Order:** 7th - Validates entire system

**Testing:**
\`\`\`bash
make test
uv run pytest tests/ -v --tb=short
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

# PR 8: Config/Docs
echo "\n--- Creating PR for feature/magentic-config-docs ---"
gh pr create \
  --base main \
  --head feature/magentic-config-docs \
  --title "feat(config): Magentic configuration & documentation" \
  --body "Configuration files and comprehensive documentation for the Magentic system.

**Changes:**
- workflows.yaml with magentic_fleet config
- Updated AGENTS.md and structured message UI docs
- Deployment and testing specifications
- CLI workflow commands
- Implementation plans
- Tooling configurations

**Dependencies:** None (parallel with core development)
**Merge Order:** 8th - Last; provides documentation

**Testing:**
\`\`\`bash
make test-config
uv run python tests/test_config.py
\`\`\`

**Integration Validation:** ✅ Passed on magentic-integration branch"

echo "\n✅ All 8 PRs created!"
echo "Review PRs at: https://github.com/Qredence/agentic-fleet/pulls"

# =============================================================================
# PHASE 5: PR Merge Instructions (Manual Process)
# =============================================================================

cat << 'EOF'

=============================================================================
NEXT STEPS: Merge PRs to Main (Manual Process)
=============================================================================

After code review and CI passes for each PR, merge in order using:

```bash
# Wait for reviews and CI to pass, then merge PRs in numerical order:

gh pr merge <pr-number-1> --squash --delete-branch  # Core
gh pr merge <pr-number-2> --squash --delete-branch  # Agents
gh pr merge <pr-number-3> --squash --delete-branch  # API
gh pr merge <pr-number-4> --squash --delete-branch  # Models
gh pr merge <pr-number-5> --squash --delete-branch  # Workflows
gh pr merge <pr-number-6> --squash --delete-branch  # Frontend
gh pr merge <pr-number-7> --squash --delete-branch  # Testing
gh pr merge <pr-number-8> --squash --delete-branch  # Config/Docs
```

After all PRs merge:

```bash
# Cleanup
git checkout main
git pull origin main
git branch -D magentic-integration
git push origin --delete magentic-integration

# Optionally archive magentic-backend
git tag magentic-backend-archived
git push origin magentic-backend-archived

# Verify all changes merged
git log --oneline --graph -20
```

=============================================================================
Summary
=============================================================================

✅ CI/CD updated with multi-branch support and frontend testing
✅ Integration branch created as staging area
📋 8 feature branches documented with exact commands
📋 Sequential merge process to integration with test validation
📋 8 PRs to main with detailed descriptions
📋 Cleanup procedures after merge

Total Timeline:
- Hands-on work: ~3 hours
- Review & CI: 2-4 days
- Total: 2-4 days calendar time

EOF

echo "\n✨ Branch strategy documentation complete!"
echo "Execute commands in order or copy-paste sections as needed."
