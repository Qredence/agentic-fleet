from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.server import create_app


def test_conversation_creation_listing_and_detail() -> None:
    with TestClient(create_app()) as client:
        create_response = client.post("/v1/conversations")
        assert create_response.status_code == status.HTTP_201_CREATED

        created = create_response.json()
        assert "id" in created
        assert isinstance(created["created_at"], int)
        assert created["messages"] == []

        list_response = client.get("/v1/conversations")
        assert list_response.status_code == status.HTTP_200_OK

        payload = list_response.json()
        assert "items" in payload
        assert any(item["id"] == created["id"] for item in payload["items"])

        detail_response = client.get(f"/v1/conversations/{created['id']}")
        assert detail_response.status_code == status.HTTP_200_OK
        detail = detail_response.json()
        assert detail["id"] == created["id"]
        assert detail["messages"] == []

        missing_response = client.get("/v1/conversations/does-not-exist")
        assert missing_response.status_code == status.HTTP_404_NOT_FOUND


def test_chat_endpoint_appends_messages() -> None:
    with TestClient(create_app()) as client:
        create_response = client.post("/v1/conversations")
        conversation_id = create_response.json()["id"]

        chat_response = client.post(
            "/v1/chat",
            json={"conversation_id": conversation_id, "message": "Summarise AgenticFleet"},
        )
        assert chat_response.status_code == status.HTTP_200_OK

        payload = chat_response.json()
        assert payload["conversation_id"] == conversation_id
        assert isinstance(payload["message"], str)

        messages = payload["messages"]
        assert len(messages) == 2
        assert [message["role"] for message in messages] == ["user", "assistant"]

        latest_detail = client.get(f"/v1/conversations/{conversation_id}")
        assert latest_detail.status_code == status.HTTP_200_OK
        detail_payload = latest_detail.json()
        assert len(detail_payload["messages"]) == 2


def test_chat_endpoint_requires_existing_conversation() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/chat",
            json={"conversation_id": "missing", "message": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
