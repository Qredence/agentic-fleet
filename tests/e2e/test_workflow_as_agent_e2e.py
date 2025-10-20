"""End-to-end tests for workflow_as_agent using Playwright."""

import pytest


@pytest.mark.e2e
class TestWorkflowAsAgentE2E:
    """End-to-end tests for workflow_as_agent frontend integration."""

    @pytest.mark.asyncio
    async def test_api_entities_includes_workflow_as_agent(self):
        """Verify workflow_as_agent appears in /v1/entities endpoint."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/v1/entities")
            assert response.status_code == 200

            data = response.json()
            entities = data.get("entities", [])

            # Find workflow_as_agent
            workflow = next((e for e in entities if e["id"] == "workflow_as_agent"), None)

            assert workflow is not None, "workflow_as_agent not found in entities"
            assert workflow["type"] == "workflow"
            assert workflow["name"] == "Reflection & Retry Workflow"
            assert "worker" in workflow["executors"]
            assert "reviewer" in workflow["executors"]
            assert workflow["metadata"]["pattern"] == "reflection"
            assert workflow["metadata"]["quality_assurance"] is True

    @pytest.mark.asyncio
    async def test_api_health_check(self):
        """Verify backend health endpoint."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data

    @pytest.mark.asyncio
    async def test_workflow_as_agent_execution(self):
        """Test workflow_as_agent execution via API."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/responses",
                json={
                    "entity_id": "workflow_as_agent",
                    "user_text": "What is 2+2?",
                },
            )

            # Collect SSE stream
            content = response.text
            assert len(content) > 0, "No response received from workflow"

            # Should contain some kind of answer
            assert "4" in content or "four" in content.lower()


# Standalone test runner
if __name__ == "__main__":
    print("Running workflow_as_agent E2E tests...")
    print("=" * 60)

    # Run tests
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
