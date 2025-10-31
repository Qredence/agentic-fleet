"""Regression tests for approval flows and conversation store utilities.

These tests replace legacy database/session checks with coverage that reflects
the current REST-first architecture. They focus on:

- Approvals API request/response validation
- Conversation store message persistence semantics
- Health endpoint structure guarantees
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.api.app import create_app
from agentic_fleet.api.conversations.service import ConversationStore


@pytest.fixture
def client() -> Iterable[TestClient]:
    """Provide a TestClient backed by the FastAPI application."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestApprovalsEndpoint:
    """Validate request/response behaviour for the approvals endpoints."""

    def test_submit_approval_decision(self, client: TestClient) -> None:
        response = client.post(
            "/v1/approvals/abc-123",
            json={"decision": "approved", "reason": "Looks good"},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload == {
            "request_id": "abc-123",
            "status": "received",
            "decision": "approved",
        }

    def test_submit_approval_requires_decision(self, client: TestClient) -> None:
        response = client.post("/v1/approvals/missing-decision", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestConversationStore:
    """Unit tests covering the in-memory conversation store."""

    def test_store_round_trip(self) -> None:
        store = ConversationStore()
        conversation = store.create(title="Test")
        message = store.add_message(conversation.id, role="user", content="Hello")

        stored = store.get(conversation.id)

        assert stored.id == conversation.id
        assert stored.messages == [message]

    def test_store_preserves_message_order(self) -> None:
        store = ConversationStore()
        conversation = store.create(title="Order Test")

        first = store.add_message(
            conversation.id,
            role="user",
            content="First",
        )
        second = store.add_message(
            conversation.id,
            role="assistant",
            content="Second",
        )

        stored = store.get(conversation.id)

        assert stored.messages[0] == first
        assert stored.messages[1] == second


class TestHealthEndpoint:
    """Smoke tests around the health endpoint contract."""

    def test_health_structure(self, client: TestClient) -> None:
        response = client.get("/v1/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
