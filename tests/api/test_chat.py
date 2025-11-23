import json
from types import SimpleNamespace

import pytest
from agent_framework import MagenticAgentMessageEvent, WorkflowOutputEvent, WorkflowStatusEvent
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def stub_supervisor_workflow(monkeypatch):
    """Stub supervisor workflow to avoid real LLM env dependencies."""

    async def _fake_workflow_factory():
        class _FakeWorkflow:
            async def run(self, message: str):
                return {"result": f"Echo: {message}"}

            async def run_stream(self, message: str):
                # Minimal events to drive SSE pipeline in the router
                yield WorkflowStatusEvent(state="running", data=None)
                yield MagenticAgentMessageEvent(
                    agent_id="test",
                    message=SimpleNamespace(text=f"Echo: {message}"),
                )
                yield WorkflowOutputEvent(
                    data={"result": f"Echo: {message}"},
                    source_executor_id="test",
                )

        return _FakeWorkflow()

    monkeypatch.setattr(
        "agentic_fleet.api.routes.chat.create_supervisor_workflow",
        _fake_workflow_factory,
    )


def test_create_conversation(client: TestClient):
    response = client.post("/api/conversations", json={"title": "Test Chat"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Chat"
    assert "id" in data
    assert "created_at" in data
    assert data["messages"] == []


def test_list_conversations(client: TestClient):
    # Create a conversation first
    client.post("/api/conversations", json={"title": "Chat 1"})
    client.post("/api/conversations", json={"title": "Chat 2"})

    response = client.get("/api/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2


def test_get_conversation(client: TestClient):
    # Create
    create_res = client.post("/api/conversations", json={"title": "Target Chat"})
    conv_id = create_res.json()["id"]

    # Get
    response = client.get(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["title"] == "Target Chat"


def test_get_conversation_not_found(client: TestClient):
    response = client.get("/api/conversations/non-existent-id")
    assert response.status_code == 404


def test_chat_non_streaming(client: TestClient):
    # Create
    create_res = client.post("/api/conversations", json={"title": "Chat"})
    conv_id = create_res.json()["id"]

    # Chat
    payload = {"conversation_id": conv_id, "message": "Hello", "stream": False}
    response = client.post("/api/chat", json=payload)
    if response.status_code != 200:
        print(f"Error Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_id
    assert data["message"] == "Echo: Hello"
    assert len(data["messages"]) > 0


def test_chat_streaming(client: TestClient):
    # Create
    create_res = client.post("/api/conversations", json={"title": "Stream Chat"})
    conv_id = create_res.json()["id"]

    # Chat
    payload = {"conversation_id": conv_id, "message": "Hello Stream", "stream": True}

    # Use client.stream for streaming endpoints
    with client.stream("POST", "/api/chat", json=payload) as response:
        assert response.status_code == 200
        lines = list(response.iter_lines())
        assert len(lines) > 0

        # Verify we get data events
        data_lines = [line for line in lines if line.startswith("data: ")]
        assert len(data_lines) > 0

        # Check for specific event types
        has_orchestrator = False
        has_delta = False
        has_completed = False

        for line in data_lines:
            content = line.replace("data: ", "")
            if content == "[DONE]":
                continue

            try:
                data = json.loads(content)
                msg_type = data.get("type")
                if msg_type == "orchestrator.message":
                    has_orchestrator = True
                elif msg_type == "response.delta":
                    has_delta = True
                elif msg_type == "response.completed":
                    has_completed = True
            except json.JSONDecodeError:
                pass

        assert has_orchestrator
        assert has_delta
        assert has_completed


def test_chat_conversation_not_found(client: TestClient):
    payload = {"conversation_id": "non-existent", "message": "Hello", "stream": False}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 404
