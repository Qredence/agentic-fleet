import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_framework import MagenticAgentMessageEvent, WorkflowOutputEvent, WorkflowStatusEvent
from fastapi.testclient import TestClient

from agentic_fleet.api.db.session import get_db_session
from agentic_fleet.api.main import app


# Mock DB session
@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def client(mock_db_session):
    # Override get_db_session
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("agentic_fleet.api.routes.chat.conversation_service")
@patch("agentic_fleet.api.routes.chat.create_supervisor_workflow")
async def test_chat_streaming(mock_create_workflow, mock_service, client):
    # Mock workflow
    mock_workflow = AsyncMock()
    mock_create_workflow.return_value = mock_workflow

    # Mock run_stream to yield events
    async def mock_stream(message):
        # Yield status
        yield WorkflowStatusEvent(state="running", data=None)
        # Yield content
        msg = MagicMock()
        msg.text = "Hello "
        yield MagenticAgentMessageEvent(agent_id="orchestrator", message=msg)
        msg2 = MagicMock()
        msg2.text = "World"
        yield MagenticAgentMessageEvent(agent_id="orchestrator", message=msg2)
        # Yield completion
        yield WorkflowOutputEvent(data={}, source_executor_id="orchestrator")

    mock_workflow.run_stream = mock_stream

    # Mock service
    mock_service.get_conversation = AsyncMock(return_value=MagicMock(id=1, messages=[]))
    mock_service.add_message_to_conversation = AsyncMock()

    # Note: TestClient is synchronous, but it handles async endpoints.
    # However, for streaming, we iterate over lines.
    response = client.post("/api/chat", json={"conversation_id": "1", "message": "Hi"})
    assert response.status_code == 200

    # Verify streaming content
    content = ""
    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    events.append(data)
                    if data["type"] == "response.delta":
                        content += data["delta"]
                except json.JSONDecodeError:
                    pass

    assert content == "Hello World"
    assert any(e["type"] == "orchestrator.message" and e["kind"] == "thought" for e in events)
    assert any(e["type"] == "response.completed" for e in events)
