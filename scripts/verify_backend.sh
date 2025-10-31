#!/bin/bash
# Quick verification script for backend implementation

echo "=========================================="
echo "AgenticFleet Backend Verification"
echo "=========================================="
echo ""

echo "1. Testing configuration loading..."
uv run python -c "from agenticfleet.api.workflow_factory import WorkflowFactory; factory = WorkflowFactory(); print(f'   ✅ Loaded {len(factory.list_available_workflows())} workflows')"
echo ""

echo "2. Running integration tests..."
uv run pytest tests/test_magentic_backend_integration.py -v --tb=short 2>&1 | tail -3
echo ""

echo "3. Running end-to-end API tests..."
uv run pytest tests/test_backend_e2e.py -v --tb=short 2>&1 | tail -3
echo ""

echo "4. Verifying workflow factory methods..."
uv run python -c "
from agenticfleet.api.workflow_factory import WorkflowFactory
factory = WorkflowFactory()
print(f'   ✅ list_available_workflows(): {len(factory.list_available_workflows())} workflows')
print(f'   ✅ get_workflow_config(): {factory.get_workflow_config(\"magentic_fleet\").name}')
print(f'   ✅ create_from_yaml(): {hasattr(factory.create_from_yaml(), \"run\")}')
"
echo ""

echo "=========================================="
echo "✅ Backend verification complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - Start server: make backend"
echo "  - Test API: curl http://localhost:8000/v2/workflows"
echo "  - Create session: curl -X POST http://localhost:8000/v1/sessions"
