"""Unit tests for Mem0ContextProvider."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agenticfleet.config import settings
from agenticfleet.context.mem0_provider import Mem0ContextProvider


@pytest.fixture
def mock_env_vars(monkeypatch: Any) -> None:
    """Set up required environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("MEM0_HISTORY_DB_PATH", "tests/.tmp/mem0-history.db")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini", raising=False)
    monkeypatch.setattr(settings, "openai_embedding_model", "text-embedding-3-small", raising=False)
    monkeypatch.setattr(
        settings, "mem0_history_db_path", "tests/.tmp/mem0-history.db", raising=False
    )


@pytest.fixture
def mock_memory() -> Any:
    """Patch the Mem0 Memory class and provide the mock instance."""
    with patch("agenticfleet.context.mem0_provider.Memory") as mock_mem:
        mock_instance = MagicMock()
        mock_mem.return_value = mock_instance
        yield mock_mem, mock_instance


class TestMem0ContextProviderInitialization:
    """Tests covering Mem0ContextProvider construction."""

    def test_init_with_defaults(self, mock_env_vars: Any, mock_memory: Any) -> None:
        """Default IDs should be applied and Memory invoked with OpenAI config."""
        mock_mem_cls, mock_instance = mock_memory

        provider = Mem0ContextProvider()

        assert provider.user_id == "agenticfleet_user"
        assert provider.agent_id == "orchestrator"
        assert provider.memory is mock_instance

        # Assert Memory was initialized directly with expected config
        assert mock_mem_cls.call_count == 1
        _, kwargs = mock_mem_cls.call_args
        config = kwargs["config"]
        assert hasattr(config, "llm")
        assert hasattr(config, "embedder")
        assert hasattr(config, "history_db_path")
        assert config.llm.provider == "openai"
        assert config.llm.config["model"] == settings.openai_model
        assert config.embedder.provider == "openai"
        assert config.embedder.config["model"] == settings.openai_embedding_model
        assert Path(config.history_db_path).name == Path(settings.mem0_history_db_path).name

    def test_init_with_custom_ids(self, mock_env_vars: Any, mock_memory: Any) -> None:
        """Custom user/agent identifiers should persist on the provider."""
        _, mock_instance = mock_memory

        provider = Mem0ContextProvider(user_id="custom_user", agent_id="custom_agent")

        assert provider.user_id == "custom_user"
        assert provider.agent_id == "custom_agent"
        assert provider.memory is mock_instance

    def test_history_path_created(
        self, mock_env_vars: Any, tmp_path: Any, mock_memory: Any
    ) -> None:
        """Mem0 history directory should be created automatically when missing."""
        history_db = tmp_path / "history" / "mem0.db"
        with patch(
            "agenticfleet.context.mem0_provider.settings.mem0_history_db_path",
            str(history_db),
        ):
            Mem0ContextProvider()

        assert history_db.parent.exists()


class TestMem0ContextProviderGet:
    """Tests for the retrieval helper."""

    def test_get_with_results(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = [
            {"memory": "User prefers Python", "score": 0.95},
            {"memory": "User likes machine learning", "score": 0.88},
        ]

        provider = Mem0ContextProvider()
        result = provider.get("What does the user like?")

        assert result == "User prefers Python\nUser likes machine learning"
        mock_instance.search.assert_called_once_with(
            "What does the user like?",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
        )

    def test_get_with_empty_results(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = []

        provider = Mem0ContextProvider()
        assert provider.get("What does the user like?") == ""

    def test_get_with_custom_ids(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = [{"memory": "Test memory", "score": 0.9}]

        provider = Mem0ContextProvider()
        provider.get("query", user_id="alice", agent_id="researcher")

        mock_instance.search.assert_called_once_with(
            "query", user_id="alice", agent_id="researcher"
        )

    def test_get_with_missing_memory_key(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = [
            {"memory": "Valid memory", "score": 0.9},
            {"score": 0.8},
            {"memory": "", "score": 0.7},
        ]

        provider = Mem0ContextProvider()
        assert provider.get("query") == "Valid memory"

    def test_get_handles_exception(self, mock_env_vars: Any, mock_memory: Any, capsys: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.side_effect = Exception("Search failed")

        provider = Mem0ContextProvider()
        assert provider.get("query") == ""

        captured = capsys.readouterr()
        assert "Error searching memories: Search failed" in captured.out

    def test_get_with_non_dict_results(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = ["string_result", 123, None]

        provider = Mem0ContextProvider()
        assert provider.get("query") == ""

    def test_get_fallback_to_default_ids(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.search.return_value = [{"memory": "Test", "score": 0.9}]

        provider = Mem0ContextProvider(user_id="default_user", agent_id="default_agent")
        provider.get("query", user_id=None, agent_id=None)

        mock_instance.search.assert_called_once_with(
            "query", user_id="default_user", agent_id="default_agent"
        )


class TestMem0ContextProviderAdd:
    """Tests for persisting new memories."""

    def test_add_with_defaults(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        provider = Mem0ContextProvider()
        provider.add("User likes Python")

        mock_instance.add.assert_called_once_with(
            "User likes Python",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata={},
        )

    def test_add_with_custom_ids(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        provider = Mem0ContextProvider()
        provider.add("Test data", user_id="alice", agent_id="researcher")

        mock_instance.add.assert_called_once_with(
            "Test data", user_id="alice", agent_id="researcher", metadata={}
        )

    def test_add_with_metadata(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        metadata = {"category": "preferences", "importance": "high"}

        provider = Mem0ContextProvider()
        provider.add("User data", metadata=metadata)

        mock_instance.add.assert_called_once_with(
            "User data",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata=metadata,
        )

    def test_add_handles_exception(self, mock_env_vars: Any, mock_memory: Any, capsys: Any) -> None:
        _, mock_instance = mock_memory
        mock_instance.add.side_effect = Exception("Add failed")

        provider = Mem0ContextProvider()
        provider.add("Test data")

        captured = capsys.readouterr()
        assert "Error adding memory: Add failed" in captured.out

    def test_add_fallback_to_default_ids(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        provider = Mem0ContextProvider(user_id="default_user", agent_id="default_agent")
        provider.add("Test data", user_id=None, agent_id=None)

        mock_instance.add.assert_called_once_with(
            "Test data",
            user_id="default_user",
            agent_id="default_agent",
            metadata={},
        )

    def test_add_with_empty_metadata(self, mock_env_vars: Any, mock_memory: Any) -> None:
        _, mock_instance = mock_memory
        provider = Mem0ContextProvider()
        provider.add("Test data", metadata=None)

        mock_instance.add.assert_called_once_with(
            "Test data",
            user_id="agenticfleet_user",
            agent_id="orchestrator",
            metadata={},
        )


class TestMem0ContextProviderConfiguration:
    """Configuration-level assertions."""

    def test_memory_receives_expected_config(self, mock_env_vars: Any) -> None:
        with patch("agenticfleet.context.mem0_provider.Memory") as patched_memory:
            Mem0ContextProvider()

            _, kwargs = patched_memory.call_args
            config = kwargs["config"]
            assert config.llm.provider == "openai"
            assert config.embedder.provider == "openai"
            assert Path(config.history_db_path).name == Path(settings.mem0_history_db_path).name
