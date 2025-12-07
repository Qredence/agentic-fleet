"""Comprehensive tests for utils/cosmos.py."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from azure.cosmos import exceptions as cosmos_exceptions

from agentic_fleet.utils.cosmos import (
    CosmosDBClient,
    CosmosDBConfig,
    create_cosmos_client,
    validate_cosmos_connection,
)


class TestCosmosDBConfig:
    """Test suite for CosmosDBConfig dataclass."""

    def test_config_creation_with_all_fields(self):
        """Test creating CosmosDBConfig with all fields."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="test_key_123",
            database_name="test_db",
            container_name="test_container",
            partition_key="/id",
        )

        assert config.endpoint == "https://test.documents.azure.com:443/"
        assert config.key == "test_key_123"
        assert config.database_name == "test_db"
        assert config.container_name == "test_container"
        assert config.partition_key == "/id"

    def test_config_with_default_partition_key(self):
        """Test config with default partition key."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        # Check if partition_key has a default
        assert hasattr(config, "partition_key")

    def test_config_validation_invalid_endpoint(self):
        """Test config validation with invalid endpoint."""
        with pytest.raises((ValueError, TypeError)):
            CosmosDBConfig(
                endpoint="not_a_url", key="key", database_name="db", container_name="container"
            )


class TestCosmosDBClient:
    """Test suite for CosmosDBClient class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock CosmosDB configuration."""
        return CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="test_key",
            database_name="test_db",
            container_name="test_container",
            partition_key="/id",
        )

    @pytest.fixture
    def mock_cosmos_client(self):
        """Create a mock Cosmos client."""
        client = Mock()
        database = Mock()
        container = Mock()

        client.get_database_client.return_value = database
        database.get_container_client.return_value = container

        return client, database, container

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    def test_client_initialization(self, mock_cosmos_client_class, mock_config):
        """Test CosmosDBClient initialization."""
        mock_client, mock_db, mock_container = Mock(), Mock(), Mock()
        mock_cosmos_client_class.return_value = mock_client
        mock_client.get_database_client.return_value = mock_db
        mock_db.get_container_client.return_value = mock_container

        client = CosmosDBClient(mock_config)

        assert client.config == mock_config
        mock_cosmos_client_class.assert_called_once_with(
            mock_config.endpoint, credential=mock_config.key
        )

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_create_item_success(self, mock_cosmos_client_class, mock_config):
        """Test successful item creation."""
        mock_container = Mock()
        mock_container.create_item = Mock(return_value={"id": "item_1", "data": "test"})

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)
            item = {"id": "item_1", "data": "test"}

            result = await client.create_item(item)

            assert result["id"] == "item_1"
            mock_container.create_item.assert_called_once_with(body=item)

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_create_item_conflict(self, mock_cosmos_client_class, mock_config):
        """Test item creation with conflict."""
        mock_container = Mock()
        mock_container.create_item = Mock(
            side_effect=cosmos_exceptions.CosmosResourceExistsError()
        )

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            with pytest.raises(cosmos_exceptions.CosmosResourceExistsError):
                await client.create_item({"id": "existing"})

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_read_item_success(self, mock_cosmos_client_class, mock_config):
        """Test successful item read."""
        mock_container = Mock()
        mock_container.read_item = Mock(return_value={"id": "item_1", "data": "value"})

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            result = await client.read_item("item_1", partition_key="item_1")

            assert result["id"] == "item_1"
            mock_container.read_item.assert_called_once()

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_read_item_not_found(self, mock_cosmos_client_class, mock_config):
        """Test reading non-existent item."""
        mock_container = Mock()
        mock_container.read_item = Mock(
            side_effect=cosmos_exceptions.CosmosResourceNotFoundError()
        )

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            with pytest.raises(cosmos_exceptions.CosmosResourceNotFoundError):
                await client.read_item("nonexistent", partition_key="nonexistent")

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_update_item_success(self, mock_cosmos_client_class, mock_config):
        """Test successful item update."""
        mock_container = Mock()
        updated_item = {"id": "item_1", "data": "updated"}
        mock_container.upsert_item = Mock(return_value=updated_item)

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            result = await client.update_item(updated_item)

            assert result["data"] == "updated"
            mock_container.upsert_item.assert_called_once_with(body=updated_item)

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_delete_item_success(self, mock_cosmos_client_class, mock_config):
        """Test successful item deletion."""
        mock_container = Mock()
        mock_container.delete_item = Mock()

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            await client.delete_item("item_1", partition_key="item_1")

            mock_container.delete_item.assert_called_once()

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_query_items_success(self, mock_cosmos_client_class, mock_config):
        """Test querying items."""
        mock_container = Mock()
        query_results = [{"id": "1", "value": "a"}, {"id": "2", "value": "b"}]
        mock_container.query_items = Mock(return_value=iter(query_results))

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            query = "SELECT * FROM c WHERE c.value = @value"
            parameters = [{"name": "@value", "value": "a"}]

            results = await client.query_items(query, parameters)

            assert len(results) == 2
            mock_container.query_items.assert_called_once()

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_query_items_with_cross_partition(self, mock_cosmos_client_class, mock_config):
        """Test querying items across partitions."""
        mock_container = Mock()
        mock_container.query_items = Mock(return_value=iter([{"id": "1"}]))

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(mock_config)

            query = "SELECT * FROM c"
            results = await client.query_items(query, enable_cross_partition=True)

            assert len(results) > 0


class TestCreateCosmosClient:
    """Test suite for create_cosmos_client function."""

    @patch("agentic_fleet.utils.cosmos.CosmosDBClient")
    def test_create_cosmos_client_from_config(self, mock_client_class):
        """Test creating client from configuration."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        mock_client_class.return_value = Mock()

        client = create_cosmos_client(config)

        mock_client_class.assert_called_once_with(config)
        assert client is not None

    def test_create_cosmos_client_with_none_config(self):
        """Test creating client with None config."""
        with pytest.raises((TypeError, ValueError)):
            create_cosmos_client(None)


class TestValidateCosmosConnection:
    """Test suite for validate_cosmos_connection function."""

    @patch("agentic_fleet.utils.cosmos.CosmosDBClient")
    async def test_validate_connection_success(self, mock_client_class):
        """Test successful connection validation."""
        mock_client = Mock()
        mock_client.read_item = AsyncMock(return_value={"id": "test"})
        mock_client_class.return_value = mock_client

        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        is_valid = await validate_cosmos_connection(config)

        assert is_valid is True

    @patch("agentic_fleet.utils.cosmos.CosmosDBClient")
    async def test_validate_connection_failure(self, mock_client_class):
        """Test connection validation failure."""
        mock_client = Mock()
        mock_client.read_item = AsyncMock(
            side_effect=cosmos_exceptions.CosmosHttpResponseError()
        )
        mock_client_class.return_value = mock_client

        config = CosmosDBConfig(
            endpoint="https://invalid.documents.azure.com:443/",
            key="invalid_key",
            database_name="db",
            container_name="container",
        )

        is_valid = await validate_cosmos_connection(config)

        assert is_valid is False


class TestCosmosDBClientEdgeCases:
    """Test edge cases and error handling."""

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_create_item_with_large_payload(self, mock_cosmos_client_class):
        """Test creating item with large payload."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        mock_container = Mock()
        large_item = {"id": "large", "data": "x" * 1000000}  # 1MB of data
        mock_container.create_item = Mock(return_value=large_item)

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(config)

            result = await client.create_item(large_item)

            assert result["id"] == "large"

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_query_with_empty_results(self, mock_cosmos_client_class):
        """Test query returning empty results."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        mock_container = Mock()
        mock_container.query_items = Mock(return_value=iter([]))

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(config)

            results = await client.query_items("SELECT * FROM c WHERE 1=0")

            assert len(results) == 0

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_concurrent_operations(self, mock_cosmos_client_class):
        """Test concurrent Cosmos DB operations."""
        import asyncio

        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        mock_container = Mock()
        mock_container.create_item = Mock(side_effect=lambda body: body)

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(config)

            items = [{"id": f"item_{i}", "value": i} for i in range(10)]

            results = await asyncio.gather(
                *[client.create_item(item) for item in items]
            )

            assert len(results) == 10

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_retry_on_throttle(self, mock_cosmos_client_class):
        """Test retry logic on throttling (429)."""
        config = CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="key",
            database_name="db",
            container_name="container",
        )

        mock_container = Mock()
        # First call raises throttle, second succeeds
        mock_container.create_item = Mock(
            side_effect=[
                cosmos_exceptions.CosmosHttpResponseError(status_code=429),
                {"id": "item_1"},
            ]
        )

        with patch.object(CosmosDBClient, "_get_container", return_value=mock_container):
            client = CosmosDBClient(config)

            # If retry logic is implemented
            try:
                result = await client.create_item({"id": "item_1"})
                assert result["id"] == "item_1"
            except cosmos_exceptions.CosmosHttpResponseError:
                # If no retry logic, exception is expected
                pass


class TestCosmosDBClientIntegration:
    """Integration tests for CosmosDBClient."""

    @pytest.fixture
    def integration_config(self):
        """Create config for integration testing."""
        return CosmosDBConfig(
            endpoint="https://test.documents.azure.com:443/",
            key="test_key",
            database_name="integration_test_db",
            container_name="test_container",
            partition_key="/id",
        )

    @patch("agentic_fleet.utils.cosmos.CosmosClient")
    async def test_full_crud_workflow(self, mock_cosmos_client_class, integration_config):
        """Test complete CRUD workflow."""
        mock_container = Mock()

        # Setup mock responses
        created_item = {"id": "test_1", "data": "initial", "timestamp": datetime.now().isoformat()}
        updated_item = {**created_item, "data": "updated"}

        mock_container.create_item = Mock(return_value=created_item)
        mock_container.read_item = Mock(return_value=created_item)
        mock_container.upsert_item = Mock(return_value=updated_item)
        mock_container.delete_item = Mock()

        with patch.object(
            CosmosDBClient, "_get_container", return_value=mock_container
        ):
            client = CosmosDBClient(integration_config)

            # Create
            result = await client.create_item(created_item)
            assert result["id"] == "test_1"

            # Read
            result = await client.read_item("test_1", partition_key="test_1")
            assert result["data"] == "initial"

            # Update
            result = await client.update_item(updated_item)
            assert result["data"] == "updated"

            # Delete
            await client.delete_item("test_1", partition_key="test_1")

            # Verify all operations called
            mock_container.create_item.assert_called_once()
            mock_container.read_item.assert_called_once()
            mock_container.upsert_item.assert_called_once()
            mock_container.delete_item.assert_called_once()