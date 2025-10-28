from __future__ import annotations

import json

from fastapi import status
from fastapi.testclient import TestClient

from agenticfleet.server import create_app


def test_conversation_creation_and_listing() -> None:
    with TestClient(create_app()) as client:
        create_response = client.post("/v1/conversations")
        assert create_response.status_code == status.HTTP_201_CREATED

        created = create_response.json()
        assert "id" in created
        assert isinstance(created["created_at"], int)
        assert isinstance(created["updated_at"], int)
        assert created["metadata"] == {}

        list_response = client.get("/v1/conversations")
        assert list_response.status_code == status.HTTP_200_OK

        payload = list_response.json()
        assert "data" in payload
        assert len(payload["data"]) == 1
        assert payload["data"][0]["id"] == created["id"]


def test_conversation_detail_items_and_deletion() -> None:
    with TestClient(create_app()) as client:
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"title": "Example", "priority": 1}},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        created = create_response.json()
        conversation_id = created["id"]

        detail_response = client.get(f"/v1/conversations/{conversation_id}")
        assert detail_response.status_code == status.HTTP_200_OK

        detail = detail_response.json()
        assert detail["id"] == conversation_id
        assert detail["metadata"].get("title") == "Example"
        assert detail["metadata"].get("priority") == "1"

        items_response = client.get(f"/v1/conversations/{conversation_id}/items")
        assert items_response.status_code == status.HTTP_200_OK
        assert items_response.json() == {"data": []}

        delete_response = client.delete(f"/v1/conversations/{conversation_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        assert (
            client.get(f"/v1/conversations/{conversation_id}").status_code
            == status.HTTP_404_NOT_FOUND
        )
        assert (
            client.get(f"/v1/conversations/{conversation_id}/items").status_code
            == status.HTTP_404_NOT_FOUND
        )


def test_responses_endpoint_streams_and_updates_history() -> None:
    with TestClient(create_app()) as client:
        conv_response = client.post("/v1/conversations")
        conversation_id = conv_response.json()["id"]

        payload = {
            "model": "dynamic_orchestration",
            "conversation": conversation_id,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Summarise AgenticFleet",
                        }
                    ],
                }
            ],
        }

        with client.stream("POST", "/v1/responses", json=payload) as response:
            assert response.status_code == status.HTTP_200_OK
            assert response.headers.get("content-type", "").startswith("text/event-stream")

            raw_events: list[str] = []
            for chunk in response.iter_lines():
                if not chunk:
                    continue
                text = chunk.decode() if isinstance(chunk, bytes) else chunk
                if text.startswith("data: "):
                    raw_events.append(text[6:])

        assert raw_events, "Expected SSE events from responses endpoint"
        assert raw_events[-1] == "[DONE]"

        workflow_event = json.loads(raw_events[0])
        assert workflow_event["type"] == "workflow.event"
        delta_event = json.loads(raw_events[1])
        assert delta_event["type"] == "response.output_text.delta"
        completion_event = json.loads(raw_events[2])
        assert completion_event["type"] == "response.completed"
        assert completion_event["response"]["conversation_id"] == conversation_id

        history_response = client.get(f"/v1/conversations/{conversation_id}/items")
        assert history_response.status_code == status.HTTP_200_OK

        history_payload = history_response.json()
        records = history_payload.get("data", [])
        assert len(records) == 2
        roles = {record.get("role") for record in records}
        assert roles == {"user", "assistant"}

        assistant_entry = next(record for record in records if record.get("role") == "assistant")
        blocks = assistant_entry.get("content", [])
        assert blocks and blocks[0].get("type") == "output_text"
        assert "AgenticFleet" in blocks[0].get("text", "")
