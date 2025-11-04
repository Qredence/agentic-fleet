#!/bin/bash
set -e

echo "Creating 8 Pull Requests..."

# PR 1: Core
gh pr create --base main --head feature/magentic-core \
  --title "feat(core): Add Magentic One orchestration framework" \
  --body "## Overview
Adds the core Magentic One orchestration framework with PLAN→EVALUATE→ACT→OBSERVE cycle.

## Changes (15 files)
- \`src/agentic_fleet/core/\` - MagenticOrchestrator, agents, events, tools
- \`console.py\` - CLI for workflow interaction
- \`main.py\` - Application entry point
- \`pyproject.toml\`, \`uv.lock\` - Dependency updates

## Dependencies
- **First PR** - Must merge before others

## Testing
\`\`\`bash
uv run pytest tests/test_magentic_backend_integration.py -k test_core
\`\`\`

Part of 8-PR split from #290"

# PR 2: Agents
gh pr create --base main --head feature/magentic-agents \
  --title "feat(agents): Add five specialist agents with prompts" \
  --body "## Overview
Implements five specialist agents for task execution.

## Changes (15 files)
- \`agents/\` - Planner, Executor, Coder, Verifier, Generator, Coordinator
- \`prompts/\` - Agent-specific prompt templates
- \`AGENTS.md\` - Documentation updates

## Dependencies
- **Depends on**: #PR1 (core)

## Testing
\`\`\`bash
uv run pytest tests/test_magentic_backend_integration.py -k test_agents
\`\`\`

Part of 8-PR split from #290"

# PR 3: API
gh pr create --base main --head feature/magentic-api-responses \
  --title "feat(api): Add OpenAI Responses API with SSE streaming" \
  --body "## Overview
Implements OpenAI-compatible responses endpoint with Server-Sent Events streaming.

## Changes (20 files)
- \`api/responses/\` - OpenAI Responses API implementation
- \`api/entities/\` - Entity discovery service
- \`api/conversations/\` - Conversation management
- \`api/chat/\`, \`api/workflows/\` - Route updates
- \`docs/api/\` - API documentation

## Dependencies
- **Depends on**: #PR1 (core), #PR2 (agents)

## Testing
\`\`\`bash
uv run pytest tests/test_api_responses.py tests/test_api_entities.py
\`\`\`

Part of 8-PR split from #290"

# PR 4: Models
gh pr create --base main --head feature/magentic-models-utils \
  --title "feat(models): Add Pydantic models and utility functions" \
  --body "## Overview
Adds data models and utility functions for the framework.

## Changes (17 files)
- \`models/\` - Entity, conversation, event, response models
- \`utils/\` - Configuration, logging, performance utilities
- \`tools/\` - Tool registry and MCP integration

## Dependencies
- **Depends on**: #PR1 (core)

## Testing
\`\`\`bash
uv run pytest tests/test_config.py
\`\`\`

Part of 8-PR split from #290"

# PR 5: Workflows
gh pr create --base main --head feature/magentic-workflows \
  --title "feat(workflows): Add MagenticBuilder and workflow orchestration" \
  --body "## Overview
Implements MagenticFleetBuilder and workflow orchestration system.

## Changes (7 files)
- \`workflow/\` - Builder, executor, event handling
- \`workflow.yaml\`, \`config/workflows.yaml\` - Configuration

## Dependencies
- **Depends on**: #PR1 (core), #PR2 (agents), #PR4 (models)

## Testing
\`\`\`bash
uv run pytest tests/test_workflow.py tests/test_workflow_factory.py
\`\`\`

Part of 8-PR split from #290"

# PR 6: Frontend
gh pr create --base main --head feature/magentic-frontend \
  --title "feat(frontend): Enhance UI with chain-of-thought display" \
  --body "## Overview
Enhances React frontend with chain-of-thought visualization and SSE integration.

## Changes (63 files)
- \`components/\` - Chain-of-thought, structured message components
- \`stores/\` - Chat and metrics state management
- \`lib/parsers/\` - Enhanced message parsing
- \`test/\`, \`vitest.config.ts\` - Testing framework

## Dependencies
- **Depends on**: #PR3 (API)

## Testing
\`\`\`bash
cd src/frontend && npm test && npm run lint
\`\`\`

Part of 8-PR split from #290"

# PR 7: Testing
gh pr create --base main --head feature/magentic-testing \
  --title "feat(testing): Add comprehensive test suite and load testing" \
  --body "## Overview
Adds comprehensive backend tests and load testing infrastructure.

## Changes (30 files)
- \`tests/test_*.py\` - API, integration, E2E tests  
- \`tests/load_testing/\` - Locust, k6, monitoring
- \`TESTING_GUIDE.md\` - Testing documentation

## Dependencies
- **Can merge independently** (test-only changes)

## Testing
\`\`\`bash
uv run pytest -v
cd tests/load_testing && make smoke
\`\`\`

Part of 8-PR split from #290"

# PR 8: Config & Docs
gh pr create --base main --head feature/magentic-config-docs \
  --title "feat(config): Update configuration and documentation" \
  --body "## Overview
Updates CI/CD configuration and adds comprehensive documentation.

## Changes (14 files)
- \`.github/workflows/ci.yml\` - Multi-branch CI support
- \`.github/agents/\`, \`.github/copilot-instructions.md\` - Agent specs
- \`PLANS.md\`, \`BRANCH_STRATEGY_COMMANDS.sh\` - Planning docs
- \`docs/\`, \`specs/\` - Documentation updates

## Dependencies  
- **Can merge independently** (config/docs only)

## Testing
\`\`\`bash
make check
\`\`\`

Part of 8-PR split from #290"

echo ""
echo "========================================="
echo "✅ All 8 PRs created!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Close PR #290 with a comment explaining the split"
echo "2. Review and merge PRs in order: 1→2→4→5→3→6→7→8"
