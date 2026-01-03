"""API tests for skill endpoints."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import agentic_fleet.db as db_module
import agentic_fleet.main as main_module
import agentic_fleet.skills.manager as manager_module
import agentic_fleet.skills.repository as repo_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    skills_path = tmp_path / "skills"
    monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_path)
    monkeypatch.setattr(manager_module, "SKILLS_BASE_PATH", skills_path)

    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    db_module._ENGINE = None

    monkeypatch.setattr(main_module, "_configure_dspy", lambda: None)

    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


def _create_skill_payload(skill_id: str = "web-research", team_id: str = "research") -> dict:
    return {
        "skill_id": skill_id,
        "name": "Web Research",
        "version": "1.0.0",
        "description": "Research on the web",
        "team_id": team_id,
        "tags": ["research"],
        "purpose": "Find current info",
        "when_to_use": "Need external sources",
        "how_to_apply": "Use search tools",
        "example": "Research market trends",
        "constraints": ["cite sources"],
        "prerequisites": ["browser"],
    }


def test_skill_crud_and_usage(client):
    payload = _create_skill_payload()

    create_response = client.post("/skills", json=payload)
    assert create_response.status_code == 200
    assert create_response.json()["message"] == "Skill created"

    get_response = client.get("/skills/web-research", params={"team_id": "research"})
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["metadata"]["skill_id"] == "web-research"
    assert data["metadata"]["team_id"] == "research"

    list_response = client.get("/skills", params={"team_id": "research"})
    assert list_response.status_code == 200
    skills = list_response.json()["skills"]
    assert any(skill["skill_id"] == "web-research" for skill in skills)

    update_response = client.put(
        "/skills/web-research",
        params={"team_id": "research"},
        json={"metadata": {"description": "Updated"}},
    )
    assert update_response.status_code == 200

    refreshed = client.get("/skills/web-research", params={"team_id": "research"})
    assert refreshed.json()["metadata"]["description"] == "Updated"

    usage_response = client.get("/skills/web-research/usage")
    assert usage_response.status_code == 200
    usage_data = usage_response.json()
    assert usage_data["skill_id"] == "web-research"
    assert usage_data["patterns"] == []

    delete_response = client.delete("/skills/web-research", params={"team_id": "research"})
    assert delete_response.status_code == 200

    missing = client.get("/skills/web-research", params={"team_id": "research"})
    assert missing.status_code == 404


def test_list_skills_defaults_to_default_team(client):
    payload = _create_skill_payload(skill_id="general", team_id="default")
    create_response = client.post("/skills", json=payload)
    assert create_response.status_code == 200

    list_response = client.get("/skills")
    assert list_response.status_code == 200
    skills = list_response.json()["skills"]
    assert any(skill["skill_id"] == "general" for skill in skills)
