"""End-to-end REST API regression tests for AgenticFleet backend."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentic_fleet.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_conversation_chat_flow() -> None:
    """A user can create a conversation, chat, and fetch updated history."""

    client = _client()

    conversation_response = client.post("/v1/conversations")
    assert conversation_response.status_code == 201
    conversation = conversation_response.json()
    conversation_id = conversation["id"]

    chat_response = client.post(
        "/v1/chat",
        json={"conversation_id": conversation_id, "message": "Hello world"},
    )
    assert chat_response.status_code == 200

    payload = chat_response.json()
    assert payload["conversation_id"] == conversation_id
    assert len(payload["messages"]) == 2
    assert [msg["role"] for msg in payload["messages"]] == ["user", "assistant"]

    detail_response = client.get(f"/v1/conversations/{conversation_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["messages"]) == 2


def test_chat_requires_existing_conversation() -> None:
    """Chat requests for unknown conversations return 404."""

    client = _client()
    response = client.post(
        "/v1/chat",
        json={"conversation_id": "missing", "message": "Hello"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_workflow_endpoints() -> None:
    """Workflow catalog endpoints expose magentic_fleet configuration."""

    client = _client()

    list_response = client.get("/v1/workflows")
    assert list_response.status_code == 200
    workflows = list_response.json()["workflows"]
    assert any(workflow["id"] == "magentic_fleet" for workflow in workflows)

    config_response = client.get("/v1/workflows/magentic_fleet")
    assert config_response.status_code == 200
    config = config_response.json()
    assert config["factory"] == "create_magentic_fleet_workflow"
    assert set(config["agents"].keys()) >= {"planner", "executor", "coder"}


def test_submit_approval_decision() -> None:
    """Approval route accepts and echoes decisions."""

    client = _client()
    response = client.post(
        "/v1/approvals/request-123",
        json={"decision": "approve", "reason": "Looks good"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "request-123"
    assert body["decision"] == "approve"
    assert body["status"] == "received"
