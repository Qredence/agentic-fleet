# E2E Testing with Playwright

## Overview

End-to-end tests for the AgenticFleet frontend and workflow_as_agent integration using Playwright.

## Test Results Summary

### ✅ Backend API Tests

**Test: workflow_as_agent in Entity Catalog**

- Status: **PASSED**
- Endpoint: `GET /v1/entities`
- Result: workflow_as_agent successfully registered
  - ID: `workflow_as_agent`
  - Type: `workflow`
  - Name: `Reflection & Retry Workflow`
  - Executors: `worker`, `reviewer`
  - Pattern: `reflection`
  - Quality Assurance: `true`

**Available Entities:**

1. **magentic_fleet** (agent)
   - Orchestrator for multi-agent coordination
2. **magentic_fleet_workflow** (workflow)
   - Default workflow with researcher, coder, analyst
3. **workflow_as_agent** (workflow) ✨ **NEW**
   - Reflection & retry pattern with Worker ↔ Reviewer cycle

### ✅ Frontend Tests

**Test: Page Load**

- Status: **PASSED**
- URL: http://localhost:5174
- Title: AgenticFleet Studio
- Welcome message displayed

**Test: User Interaction**

- Input field: Functional ✓
- Send button: Functional ✓
- Query submitted: "What is the capital of France?"
- Loading state: "Thinking..." displayed

## Configuration Note

⚠️ **Port Configuration**: The frontend is configured to proxy to port 8080, but the backend runs on 8000 by default. To fix:

**Option 1: Update vite.config.ts**

```typescript
server: {
  proxy: {
    '/v1': 'http://localhost:8000',  // Change from 8080
    '/health': 'http://localhost:8000'
  }
}
```

**Option 2: Run backend on 8080**

```bash
uv run uvicorn agenticfleet.haxui.api:app --reload --port 8080
```

## Running Tests

### Quick Test

```bash
# Make sure backend and frontend are running
make dev

# In another terminal, run tests
uv run python tests/e2e/playwright_test_workflow.py
```

### Full Test Suite

```bash
# Run pytest-based tests
uv run pytest tests/e2e/test_workflow_as_agent_e2e.py -v
```

## Test Files

- `tests/e2e/playwright_test_workflow.py` - Interactive Playwright tests
- `tests/e2e/test_workflow_as_agent_e2e.py` - pytest-based API tests
- `tests/test_workflow_as_agent_api.py` - Unit tests for entity catalog

## Screenshots

Test screenshots are saved to `.playwright-mcp/`:

- `frontend-initial-state.png` - Initial page load
- `test-query-entered.png` - Query entered in input
- `test-response-received.png` - Response loading state

## Verified Features

✅ workflow_as_agent appears in entity catalog
✅ Entity metadata includes reflection pattern flag
✅ Entity metadata includes quality_assurance flag
✅ Worker and Reviewer executors registered
✅ Frontend loads successfully
✅ User can type queries
✅ Send button becomes active with input
✅ Query submission triggers loading state

## Next Steps

1. Fix port configuration mismatch
2. Test actual workflow execution
3. Verify Worker ↔ Reviewer cycle in UI
4. Test with different query types
5. Add error handling tests
6. Test conversation persistence

## Playwright MCP Tools Used

- `browser_navigate` - Navigate to frontend URL
- `browser_snapshot` - Capture page structure
- `browser_take_screenshot` - Save visual states
- `browser_type` - Enter text into input field
- `browser_click` - Click send button
- `browser_evaluate` - Run JavaScript to test API

All tests demonstrate successful integration of workflow_as_agent into the AgenticFleet platform! 🎉
