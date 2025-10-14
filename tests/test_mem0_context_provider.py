"""Unit tests for Mem0ContextProvider."""

from unittest.mock import MagicMock, patch

import pytest

from agenticfleet.context.mem0_provider import Mem0ContextProvider


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test-project.openai.azure.com")
    monkeypatch.setenv("AZURE_AI_SEARCH_ENDPOINT", "https://test-service.search.windows.net")
    monkeypatch.setenv("AZURE_AI_SEARCH_KEY", "test-search-key")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME", "text-embedding-ada-002")


@pytest.fixture
def mock_memory():
    """Create a mock Memory object."""
    with patch("agenticfleet.context.mem0_provider.Memory") as mock_mem:
        mock_instance = MagicMock()
        mock_mem.from_config.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_azure_client():
    """Create a mock AzureOpenAI client."""
    with patch("agenticfleet.context.mem0_provider.AzureOpenAI") as mock_azure:
        yield mock_azure


class TestMem0ContextProviderInitialization:
    """Tests for Mem0ContextProvider initialization."""

    def test_init_with_defaults(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test initialization with default parameters."""
        provider = Mem0ContextProvider()

        assert provider.user_id == "agenticfleet_user"
        assert provider.agent_id == "orchestrator"
        assert provider.memory is not None

    def test_init_with_custom_ids(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test initialization with custom user_id and agent_id."""
        provider = Mem0ContextProvider(user_id="custom_user", agent_id="custom_agent")

        assert provider.user_id == "custom_user"
        assert provider.agent_id == "custom_agent"

    def test_init_missing_azure_project_endpoint(self, mock_memory, mock_azure_client):
        """Test initialization fails when AZURE_AI_PROJECT_ENDPOINT is missing."""
        # Mock settings with None for project endpoint
        with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
            mock_settings.azure_ai_project_endpoint = None
            mock_settings.azure_ai_search_endpoint = "https://test.search.windows.net"
            mock_settings.azure_ai_search_key = "test-key"
            mock_settings.openai_api_key = "test-key"

            with pytest.raises(ValueError, match="AZURE_AI_PROJECT_ENDPOINT"):
                Mem0ContextProvider()

    def test_init_missing_azure_search_endpoint(self, mock_memory, mock_azure_client):
        """Test initialization fails when AZURE_AI_SEARCH_ENDPOINT is missing."""
        # Mock settings with None for search endpoint
        with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
            mock_settings.azure_ai_project_endpoint = "https://test.openai.azure.com"
            mock_settings.azure_ai_search_endpoint = None
            mock_settings.azure_ai_search_key = "test-key"
            mock_settings.openai_api_key = "test-key"

            with pytest.raises(ValueError, match="AZURE_AI_SEARCH_ENDPOINT"):
                Mem0ContextProvider()

    def test_service_name_extraction_from_url(self, mock_env_vars, mock_azure_client):
        """Test that service name is correctly extracted from full URL."""
        with patch("agenticfleet.context.mem0_provider.Memory") as patched_memory:
            with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
                mock_settings.azure_ai_project_endpoint = "https://test-project.openai.azure.com"
                mock_settings.azure_ai_search_endpoint = "https://test-service.search.windows.net"
                mock_settings.azure_ai_search_key = "test-search-key"
                mock_settings.openai_api_key = "test-openai-key"
                mock_settings.azure_openai_chat_completion_deployed_model_name = "gpt-4o"
                mock_settings.azure_openai_embedding_deployed_model_name = "text-embedding-ada-002"

                patched_memory.from_config.return_value = MagicMock()

                _ = Mem0ContextProvider()

                call_args = patched_memory.from_config.call_args
                config = call_args[0][0]

                assert config["vector_store"]["config"]["service_name"] == "test-service"

    def test_service_name_without_https(self, mock_azure_client):
        """Test that service name is used as-is when not a full URL."""
        # Mock settings with non-URL service name
        with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
            mock_settings.azure_ai_project_endpoint = "https://test.openai.azure.com"
            mock_settings.azure_ai_search_endpoint = "my-service-name"
            mock_settings.azure_ai_search_key = "test-key"
            mock_settings.openai_api_key = "test-key"
            mock_settings.azure_openai_chat_completion_deployed_model_name = "gpt-4o"
            mock_settings.azure_openai_embedding_deployed_model_name = "text-embedding"

            with patch("agenticfleet.context.mem0_provider.Memory") as patched_memory:
                patched_memory.from_config.return_value = MagicMock()

                _ = Mem0ContextProvider()

                # Verify service_name is used as-is
                call_args = patched_memory.from_config.call_args
                config = call_args[0][0]

                assert config["vector_store"]["config"]["service_name"] == "my-service-name"


class TestMem0ContextProviderGet:
    """Tests for Mem0ContextProvider.get() method."""

    def test_get_with_results(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() returns concatenated memories."""
        mock_memory.search.return_value = [
            {"memory": "User prefers Python", "score": 0.95},
            {"memory": "User likes machine learning", "score": 0.88},
        ]

        provider = Mem0ContextProvider()
        result = provider.get("What does the user like?")

        assert result == "User prefers Python\nUser likes machine learning"
        mock_memory.search.assert_called_once_with(
            "What does the user like?",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
        )

    def test_get_with_empty_results(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() returns empty string when no results."""
        mock_memory.search.return_value = []

        provider = Mem0ContextProvider()
        result = provider.get("What does the user like?")

        assert result == ""

    def test_get_with_custom_ids(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() uses custom user_id and agent_id."""
        mock_memory.search.return_value = [{"memory": "Test memory", "score": 0.9}]

        provider = Mem0ContextProvider()
        _ = provider.get("query", user_id="alice", agent_id="researcher")

        mock_memory.search.assert_called_once_with("query", user_id="alice", agent_id="researcher")

    def test_get_with_missing_memory_key(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() handles results without 'memory' key gracefully."""
        mock_memory.search.return_value = [
            {"memory": "Valid memory", "score": 0.9},
            {"score": 0.8},  # Missing 'memory' key
            {"memory": "", "score": 0.7},  # Empty memory
        ]

        provider = Mem0ContextProvider()
        result = provider.get("query")

        assert result == "Valid memory"

    def test_get_handles_exception(self, mock_env_vars, mock_memory, mock_azure_client, capsys):
        """Test get() handles exceptions gracefully and returns empty string."""
        mock_memory.search.side_effect = Exception("Search failed")

        provider = Mem0ContextProvider()
        result = provider.get("query")

        assert result == ""
        captured = capsys.readouterr()
        assert "Error searching memories: Search failed" in captured.out

    def test_get_with_non_dict_results(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() handles non-dict results gracefully."""
        mock_memory.search.return_value = ["string_result", 123, None]

        provider = Mem0ContextProvider()
        result = provider.get("query")

        assert result == ""

    def test_get_fallback_to_default_ids(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test get() falls back to default IDs when None is provided."""
        mock_memory.search.return_value = [{"memory": "Test", "score": 0.9}]

        provider = Mem0ContextProvider(user_id="default_user", agent_id="default_agent")
        _ = provider.get("query", user_id=None, agent_id=None)

        mock_memory.search.assert_called_once_with(
            "query", user_id="default_user", agent_id="default_agent"
        )


class TestMem0ContextProviderAdd:
    """Tests for Mem0ContextProvider.add() method."""

    def test_add_with_defaults(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test add() with default parameters."""
        provider = Mem0ContextProvider()
        provider.add("User likes Python")

        mock_memory.add.assert_called_once_with(
            "User likes Python",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata={},
        )

    def test_add_with_custom_ids(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test add() with custom user_id and agent_id."""
        provider = Mem0ContextProvider()
        provider.add("Test data", user_id="alice", agent_id="researcher")

        mock_memory.add.assert_called_once_with(
            "Test data", user_id="alice", agent_id="researcher", metadata={}
        )

    def test_add_with_metadata(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test add() with custom metadata."""
        metadata = {"category": "preferences", "importance": "high"}

        provider = Mem0ContextProvider()
        provider.add("User data", metadata=metadata)

        mock_memory.add.assert_called_once_with(
            "User data",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata=metadata,
        )

    def test_add_handles_exception(self, mock_env_vars, mock_memory, mock_azure_client, capsys):
        """Test add() handles exceptions gracefully."""
        mock_memory.add.side_effect = Exception("Add failed")

        provider = Mem0ContextProvider()
        provider.add("Test data")  # Should not raise

        captured = capsys.readouterr()
        assert "Error adding memory: Add failed" in captured.out

    def test_add_fallback_to_default_ids(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test add() falls back to default IDs when None is provided."""
        provider = Mem0ContextProvider(user_id="default_user", agent_id="default_agent")
        provider.add("Test data", user_id=None, agent_id=None)

        mock_memory.add.assert_called_once_with(
            "Test data", user_id="default_user", agent_id="default_agent", metadata={}
        )

    def test_add_with_empty_metadata(self, mock_env_vars, mock_memory, mock_azure_client):
        """Test add() converts None metadata to empty dict."""
        provider = Mem0ContextProvider()
        provider.add("Test data", metadata=None)

        mock_memory.add.assert_called_once_with(
            "Test data",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata={},
        )


class TestMem0ContextProviderConfiguration:
    """Tests for Mem0ContextProvider configuration."""

    def test_memory_config_structure(self, mock_env_vars, mock_azure_client):
        """Test that Memory.from_config is called with correct structure."""
        with patch("agenticfleet.context.mem0_provider.Memory") as patched_memory:
            with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
                mock_settings.azure_ai_project_endpoint = "https://test-project.openai.azure.com"
                mock_settings.azure_ai_search_endpoint = "https://test-service.search.windows.net"
                mock_settings.azure_ai_search_key = "test-search-key"
                mock_settings.openai_api_key = "test-openai-key"
                mock_settings.azure_openai_chat_completion_deployed_model_name = "gpt-4o"
                mock_settings.azure_openai_embedding_deployed_model_name = "text-embedding-ada-002"

                patched_memory.from_config.return_value = MagicMock()

                _ = Mem0ContextProvider()

                # Verify from_config was called
                assert patched_memory.from_config.called

                # Get the config passed to from_config
                call_args = patched_memory.from_config.call_args
                config = call_args[0][0]

                # Verify config structure
                assert "vector_store" in config
                assert "llm" in config
                assert "embedder" in config

                # Verify vector store config
                vs_config = config["vector_store"]["config"]
                assert vs_config["service_name"] == "test-service"
                assert vs_config["api_key"] == "test-search-key"
                assert vs_config["collection_name"] == "agenticfleet-memories"
                assert vs_config["embedding_model_dims"] == 1536

                # Verify LLM config
                assert config["llm"]["provider"] == "azure_openai"
                assert config["llm"]["config"]["model"] == "gpt-4o"
                assert config["llm"]["config"]["temperature"] == 0
                assert config["llm"]["config"]["max_tokens"] == 1000

                # Verify embedder config
                assert config["embedder"]["provider"] == "azure_openai"
                assert config["embedder"]["config"]["model"] == "text-embedding-ada-002"

    def test_azure_client_initialization(self, mock_env_vars, mock_azure_client):
        """Test that AzureOpenAI client is initialized correctly."""
        with patch("agenticfleet.context.mem0_provider.Memory") as patched_memory:
            with patch("agenticfleet.context.mem0_provider.settings") as mock_settings:
                mock_settings.azure_ai_project_endpoint = "https://test-project.openai.azure.com"
                mock_settings.azure_ai_search_endpoint = "https://test-service.search.windows.net"
                mock_settings.azure_ai_search_key = "test-search-key"
                mock_settings.openai_api_key = "test-openai-key"
                mock_settings.azure_openai_chat_completion_deployed_model_name = "gpt-4o"
                mock_settings.azure_openai_embedding_deployed_model_name = "text-embedding-ada-002"

                patched_memory.from_config.return_value = MagicMock()

                _ = Mem0ContextProvider()

                mock_azure_client.assert_called_once_with(
                    azure_endpoint="https://test-project.openai.azure.com",
                    api_key="test-openai-key",
                    api_version="2025-05-01",
                )
