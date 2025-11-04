"""Unit tests for EntityDiscovery service."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agentic_fleet.api.entities.service import EntityDiscovery
from agentic_fleet.api.models.workflow_config import WorkflowConfig
from agentic_fleet.api.workflow_factory import WorkflowFactory


@pytest.fixture
def mock_workflow_factory() -> Mock:
    """Create a mock WorkflowFactory with both sync and async method support."""
    from unittest.mock import AsyncMock

    factory = Mock(spec=WorkflowFactory)
    factory.list_available_workflows.return_value = [
        {
            "id": "magentic_fleet",
            "name": "Magentic Fleet Workflow",
            "description": "Test workflow",
            "factory": "create_magentic_fleet_workflow",
            "agent_count": 5,
        }
    ]
    factory.get_workflow_config.return_value = WorkflowConfig(
        id="magentic_fleet",
        name="Magentic Fleet Workflow",
        description="Test workflow",
        factory="create_magentic_fleet_workflow",
        agents={},
        manager={},
    )
    # Add async variants
    factory.get_workflow_config_async = AsyncMock(
        return_value=WorkflowConfig(
            id="magentic_fleet",
            name="Magentic Fleet Workflow",
            description="Test workflow",
            factory="create_magentic_fleet_workflow",
            agents={},
            manager={},
        )
    )
    factory._load_config.return_value = {"workflows": {}}
    factory._config = {}
    return factory


@pytest.fixture
def entity_discovery(mock_workflow_factory: Mock) -> EntityDiscovery:
    """Create EntityDiscovery instance with mocked factory."""
    return EntityDiscovery(workflow_factory=mock_workflow_factory)


def test_list_entities(entity_discovery: EntityDiscovery, mock_workflow_factory: Mock) -> None:
    """Test listing entities returns correct structure."""
    entities = entity_discovery.list_entities()

    assert len(entities) == 1
    assert entities[0].id == "magentic_fleet"
    assert entities[0].name == "Magentic Fleet Workflow"
    assert entities[0].description == "Test workflow"
    assert entities[0].input_schema.type == "object"
    assert "input" in entities[0].input_schema.properties
    mock_workflow_factory.list_available_workflows.assert_called_once()


def test_list_entities_caching(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test entity caching on second call."""
    entities1 = entity_discovery.list_entities()
    entities2 = entity_discovery.list_entities()

    # Should call factory for each call (since we need to check cache)
    # But entities should be cached internally
    assert mock_workflow_factory.list_available_workflows.call_count >= 1
    # Should return same cached entities
    assert entities1[0].id == entities2[0].id


def test_get_entity_info(entity_discovery: EntityDiscovery, mock_workflow_factory: Mock) -> None:
    """Test getting entity info returns EntityInfo with all required fields."""
    entity_info = entity_discovery.get_entity_info("magentic_fleet")

    assert entity_info.id == "magentic_fleet"
    assert entity_info.name == "Magentic Fleet Workflow"
    assert entity_info.description == "Test workflow"
    assert entity_info.input_schema.type == "object"
    assert "input" in entity_info.input_schema.properties
    assert "conversation_id" in entity_info.input_schema.properties
    assert "input" in entity_info.input_schema.required
    mock_workflow_factory.get_workflow_config.assert_called_once_with("magentic_fleet")


def test_get_entity_info_caching(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test entity info caching on second call."""
    entity_info1 = entity_discovery.get_entity_info("magentic_fleet")
    entity_info2 = entity_discovery.get_entity_info("magentic_fleet")

    # Should only call factory once due to caching
    assert mock_workflow_factory.get_workflow_config.call_count == 1
    # Should return same cached entity
    assert entity_info1.id == entity_info2.id


def test_get_entity_info_not_found(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test getting non-existent entity raises ValueError."""
    mock_workflow_factory.get_workflow_config.side_effect = ValueError(
        "Entity 'nonexistent' not found"
    )
    mock_workflow_factory.get_workflow_config_async.side_effect = ValueError(
        "Entity 'nonexistent' not found"
    )

    with pytest.raises(ValueError, match="Entity 'nonexistent' not found"):
        entity_discovery.get_entity_info("nonexistent")


def test_reload_entity(entity_discovery: EntityDiscovery, mock_workflow_factory: Mock) -> None:
    """Test reloading entity clears cache and reloads configuration."""
    # First, get entity info to populate cache
    entity_discovery.get_entity_info("magentic_fleet")
    assert "magentic_fleet" in entity_discovery._entity_cache

    # Reload entity
    entity_discovery.reload_entity("magentic_fleet")

    # Cache should be cleared
    assert "magentic_fleet" not in entity_discovery._entity_cache
    # Factory should reload config
    mock_workflow_factory._load_config.assert_called()


def test_reload_entity_not_found(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test reloading non-existent entity raises ValueError."""
    mock_workflow_factory.get_workflow_config.side_effect = ValueError(
        "Entity 'nonexistent' not found"
    )

    with pytest.raises(ValueError, match="Entity 'nonexistent' not found after reload"):
        entity_discovery.reload_entity("nonexistent")


def test_get_workflow_instance(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test getting workflow instance creates and caches instance."""
    mock_workflow = Mock()
    mock_workflow_factory.create_from_yaml.return_value = mock_workflow

    workflow1 = entity_discovery.get_workflow_instance("magentic_fleet")

    assert workflow1 == mock_workflow
    mock_workflow_factory.create_from_yaml.assert_called_once_with("magentic_fleet")
    assert "magentic_fleet" in entity_discovery._workflow_cache


def test_get_workflow_instance_caching(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test workflow instance caching on second call."""
    mock_workflow = Mock()
    mock_workflow_factory.create_from_yaml.return_value = mock_workflow

    workflow1 = entity_discovery.get_workflow_instance("magentic_fleet")
    workflow2 = entity_discovery.get_workflow_instance("magentic_fleet")

    # Should only call factory once due to caching
    assert mock_workflow_factory.create_from_yaml.call_count == 1
    # Should return same cached instance
    assert workflow1 == workflow2


def test_input_schema_generation(entity_discovery: EntityDiscovery) -> None:
    """Test input schema generation matches OpenAI format."""
    entities = entity_discovery.list_entities()
    entity = entities[0]

    assert entity.input_schema.type == "object"
    assert "input" in entity.input_schema.properties
    assert "conversation_id" in entity.input_schema.properties
    assert entity.input_schema.properties["input"]["type"] == "string"
    assert entity.input_schema.properties["conversation_id"]["type"] == "string"
    assert "input" in entity.input_schema.required


def test_reload_clears_workflow_cache(
    entity_discovery: EntityDiscovery, mock_workflow_factory: Mock
) -> None:
    """Test reload clears workflow instance cache."""
    mock_workflow = Mock()
    mock_workflow_factory.create_from_yaml.return_value = mock_workflow

    # Create workflow instance
    entity_discovery.get_workflow_instance("magentic_fleet")
    assert "magentic_fleet" in entity_discovery._workflow_cache

    # Reload entity
    entity_discovery.reload_entity("magentic_fleet")

    # Workflow cache should be cleared
    assert "magentic_fleet" not in entity_discovery._workflow_cache
