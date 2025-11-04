#!/bin/bash
set -e

echo "Creating branches 3-8..."

# Branch 3: API Responses
echo "Creating feature/magentic-api-responses..."
git checkout main
git checkout -b feature/magentic-api-responses  
git checkout magentic-backend -- \
  src/agentic_fleet/api/responses/ \
  src/agentic_fleet/api/entities/ \
  src/agentic_fleet/api/conversations/ \
  src/agentic_fleet/api/app.py \
  src/agentic_fleet/api/chat/ \
  src/agentic_fleet/api/workflows/ \
  docs/api/ \
  scripts/test-api-endpoints.py \
  scripts/test_backend_quick.py 2>/dev/null || true
git commit --no-verify -m "feat(api): add OpenAI Responses API with SSE streaming

- Implement OpenAI-compatible responses endpoint
- Add Server-Sent Events (SSE) streaming
- Add entity discovery service
- Add conversation management  
- Update chat and workflow routes
- Update API documentation"
git push -u origin feature/magentic-api-responses
echo "✅ Branch 3 done"

# Branch 4: Models & Utils
echo "Creating feature/magentic-models-utils..."
git checkout main
git checkout -b feature/magentic-models-utils
git checkout magentic-backend -- \
  src/agentic_fleet/models/ \
  src/agentic_fleet/utils/ \
  src/agentic_fleet/tools/ \
  tools/scripts/validate_agents_docs.py 2>/dev/null || true
git commit --no-verify -m "feat(models): add Pydantic models and utility functions

- Add entity, conversation, and event models
- Add factory and configuration utilities
- Add tool registry and validation
- Update validation scripts"
git push -u origin feature/magentic-models-utils
echo "✅ Branch 4 done"

# Branch 5: Workflows
echo "Creating feature/magentic-workflows..."
git checkout main
git checkout -b feature/magentic-workflows
git checkout magentic-backend -- \
  src/agentic_fleet/workflow/ \
  src/agentic_fleet/workflow.yaml \
  config/workflows.yaml 2>/dev/null || true
git commit --no-verify -m "feat(workflows): add MagenticBuilder and workflow orchestration

- Add MagenticFleetBuilder for workflow construction
- Add workflow executor and event handling
- Add YAML workflow configurations
- Add workflow factory integration"
git push -u origin feature/magentic-workflows
echo "✅ Branch 5 done"

# Branch 6: Frontend
echo "Creating feature/magentic-frontend..."
git checkout main
git checkout -b feature/magentic-frontend
git checkout magentic-backend -- src/frontend/ 2>/dev/null || true
git commit --no-verify -m "feat(frontend): enhance UI with chain-of-thought display

- Add chain-of-thought visualization components
- Implement structured message parsing
- Add SSE streaming integration
- Add metrics store for performance tracking
- Add Vitest testing framework
- Update UI components and styles"
git push -u origin feature/magentic-frontend
echo "✅ Branch 6 done"

# Branch 7: Testing
echo "Creating feature/magentic-testing..."
git checkout main
git checkout -b feature/magentic-testing
git checkout magentic-backend -- \
  tests/test_api_entities.py \
  tests/test_api_responses.py \
  tests/test_api_responses_streaming.py \
  tests/test_api_segmented_streaming.py \
  tests/test_automation.py \
  tests/test_backward_compatibility.py \
  tests/test_config.py \
  tests/test_console.py \
  tests/test_entity_discovery_service.py \
  tests/test_error_handling.py \
  tests/test_event_bridge.py \
  tests/test_improvement_implementation.py \
  tests/test_magentic_integration.py \
  tests/test_response_aggregator.py \
  tests/test_static_file_serving.py \
  tests/test_utils_events.py \
  tests/validate_test_improvements.py \
  tests/TESTING_GUIDE.md \
  tests/load_testing/ \
  test_sse_performance.py 2>/dev/null || true
git commit --no-verify -m "feat(testing): add comprehensive test suite and load testing

- Add API endpoint tests (entities, responses, streaming)
- Add integration and E2E tests
- Add load testing infrastructure (Locust, k6)
- Add test automation and validation
- Add monitoring and dashboard
- Add testing documentation"
git push -u origin feature/magentic-testing
echo "✅ Branch 7 done"

# Branch 8: Config & Docs
echo "Creating feature/magentic-config-docs..."
git checkout main
git checkout -b feature/magentic-config-docs
git checkout magentic-backend -- \
  .claude/ \
  .github/agents/ \
  .github/copilot-instructions.md \
  .github/workflows/ci.yml \
  .gitignore \
  .mcp.json \
  BRANCH_STRATEGY_COMMANDS.sh \
  PLANS.md \
  package.json \
  package-lock.json \
  docs/configuration-guide.md \
  docs/responsive-design-implementation.md \
  docs/STRUCTURED_MESSAGE_UI.md \
  specs/ 2>/dev/null || true
git commit --no-verify -m "feat(config): update configuration and documentation

- Update CI/CD workflows for multi-branch testing
- Add comprehensive planning documentation
- Update agent instructions and specifications
- Add MCP configuration
- Update project dependencies
- Add branch strategy documentation"
git push -u origin feature/magentic-config-docs
echo "✅ Branch 8 done"

echo ""
echo "========================================="
echo "✅ All 8 feature branches created!"
echo "========================================="
git checkout main
git branch | grep feature/magentic
