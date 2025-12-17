"""Tests for compiled DSPy artifact registry."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.compiled_registry import (
    ArtifactMetadata,
    ArtifactRegistry,
    CompiledArtifact,
    _load_artifact_metadata,
    _validate_dspy_version_compatibility,
    load_required_compiled_modules,
    validate_artifact_registry,
)


class TestArtifactRegistry:
    """Tests for ArtifactRegistry dataclass."""

    def test_artifact_registry_initialization(self):
        """Test that ArtifactRegistry initializes with None values."""
        registry = ArtifactRegistry()
        assert registry.routing is None
        assert registry.tool_planning is None
        assert registry.quality is None
        assert registry.reasoner is None

    def test_get_module(self):
        """Test that get_module retrieves modules by name."""
        mock_module = MagicMock()
        registry = ArtifactRegistry(routing=mock_module)

        assert registry.get_module("routing") is mock_module
        assert registry.get_module("quality") is None
        assert registry.get_module("nonexistent") is None


class TestValidateArtifactRegistry:
    """Tests for validate_artifact_registry function."""

    def test_validate_empty_registry(self):
        """Test validation of empty registry."""
        registry = ArtifactRegistry()
        status = validate_artifact_registry(registry)

        assert status == {
            "routing": False,
            "tool_planning": False,
            "quality": False,
            "reasoner": False,
        }

    def test_validate_partially_loaded_registry(self):
        """Test validation of partially loaded registry."""
        mock_module = MagicMock()
        registry = ArtifactRegistry(routing=mock_module, quality=mock_module)
        status = validate_artifact_registry(registry)

        assert status == {
            "routing": True,
            "tool_planning": False,
            "quality": True,
            "reasoner": False,
        }


class TestLoadRequiredCompiledModules:
    """Tests for load_required_compiled_modules function."""

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    @patch("agentic_fleet.dspy_modules.compiled_registry.Path")
    def test_load_with_require_compiled_false(self, mock_path_cls, mock_load):
        """Test loading with require_compiled=False (lenient mode)."""
        # Mock path existence checks to return False (no artifacts exist)
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_cls.return_value = mock_path

        dspy_config = {
            "compiled_routing_path": ".var/cache/dspy/compiled_routing.json",
            "compiled_tool_planning_path": ".var/cache/dspy/compiled_tool_planning.json",
            "compiled_quality_path": ".var/logs/compiled_answer_quality.pkl",
            "compiled_reasoner_path": ".var/cache/dspy/compiled_reasoner.json",
        }

        # Should not raise with require_compiled=False
        registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=False,
        )

        assert registry is not None
        assert isinstance(registry, ArtifactRegistry)

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    def test_load_with_require_compiled_true_missing_artifacts(self, mock_load):
        """Test that missing required artifacts raise RuntimeError."""
        dspy_config = {
            "compiled_routing_path": "/nonexistent/routing.json",
            "compiled_tool_planning_path": "/nonexistent/tool_planning.json",
            "compiled_quality_path": "/nonexistent/quality.pkl",
        }

        # Should raise RuntimeError with require_compiled=True
        with pytest.raises(RuntimeError) as exc_info:
            load_required_compiled_modules(
                dspy_config=dspy_config,
                require_compiled=True,
            )

        error_msg = str(exc_info.value)
        assert "Missing required artifacts" in error_msg
        assert "routing" in error_msg
        assert "tool_planning" in error_msg
        assert "quality" in error_msg

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    @patch("agentic_fleet.dspy_modules.compiled_registry._resolve_artifact_path")
    def test_load_with_successful_artifacts(self, mock_resolve, mock_load):
        """Test successful loading of all artifacts."""
        # Mock successful artifact loading
        mock_module = MagicMock()
        mock_load.return_value = mock_module

        # Mock path resolution to return existing paths
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_resolve.return_value = mock_path

        dspy_config = {
            "compiled_routing_path": ".var/cache/dspy/compiled_routing.json",
            "compiled_tool_planning_path": ".var/cache/dspy/compiled_tool_planning.json",
            "compiled_quality_path": ".var/logs/compiled_answer_quality.pkl",
        }

        registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=True,
        )

        assert registry is not None
        assert registry.routing is mock_module
        assert registry.tool_planning is mock_module
        assert registry.quality is mock_module


class TestCompiledArtifact:
    """Tests for CompiledArtifact dataclass."""

    def test_compiled_artifact_creation(self):
        """Test CompiledArtifact creation."""
        artifact = CompiledArtifact(
            name="test_module",
            path=Path("/test/path.json"),
            required=True,
            description="Test module",
        )

        assert artifact.name == "test_module"
        assert artifact.path == Path("/test/path.json")
        assert artifact.required is True
        assert artifact.description == "Test module"
        assert artifact.module is None
        assert artifact.metadata is None


class TestArtifactMetadata:
    """Tests for Phase 3 ArtifactMetadata."""

    def test_metadata_creation(self):
        """Test ArtifactMetadata creation with all fields."""
        metadata = ArtifactMetadata(
            schema_version=3,
            dspy_version="3.0.5",
            created_at="2024-01-01T00:00:00",
            optimizer="gepa",
            build_id="abc123",
            serializer="pickle",
        )

        assert metadata.schema_version == 3
        assert metadata.dspy_version == "3.0.5"
        assert metadata.created_at == "2024-01-01T00:00:00"
        assert metadata.optimizer == "gepa"
        assert metadata.build_id == "abc123"
        assert metadata.serializer == "pickle"

    def test_metadata_minimal(self):
        """Test ArtifactMetadata with only required field."""
        metadata = ArtifactMetadata(schema_version=2)

        assert metadata.schema_version == 2
        assert metadata.dspy_version is None
        assert metadata.created_at is None


class TestLoadArtifactMetadata:
    """Tests for Phase 3 metadata loading."""

    def test_load_metadata_success(self, tmp_path):
        """Test loading metadata from file."""
        artifact_path = tmp_path / "test_artifact.json"
        metadata_path = Path(str(artifact_path) + ".meta")

        # Create metadata file
        metadata_data = {
            "version": 3,
            "dspy_version": "3.0.5",
            "created_at": "2024-01-01T00:00:00",
            "optimizer": "gepa",
            "build_id": "test123",
            "serializer": "pickle",
        }
        metadata_path.write_text(json.dumps(metadata_data))

        # Load metadata
        metadata = _load_artifact_metadata(artifact_path)

        assert metadata is not None
        assert metadata.schema_version == 3
        assert metadata.dspy_version == "3.0.5"
        assert metadata.optimizer == "gepa"

    def test_load_metadata_missing_file(self, tmp_path):
        """Test loading metadata when file doesn't exist."""
        artifact_path = tmp_path / "nonexistent.json"
        metadata = _load_artifact_metadata(artifact_path)
        assert metadata is None

    def test_load_metadata_invalid_json(self, tmp_path):
        """Test loading metadata with invalid JSON."""
        artifact_path = tmp_path / "test_artifact.json"
        metadata_path = Path(str(artifact_path) + ".meta")
        metadata_path.write_text("not valid json")

        metadata = _load_artifact_metadata(artifact_path)
        assert metadata is None


class TestValidateDspyVersionCompatibility:
    """Tests for Phase 3 DSPy version validation."""

    def test_compatible_version(self):
        """Test validation with compatible DSPy version."""
        # DSPy import happens inside the function, so we can test with real dspy
        metadata = ArtifactMetadata(schema_version=3, dspy_version="3.0.3")

        is_compatible, error_msg = _validate_dspy_version_compatibility(metadata)

        # Should be compatible (allowing same or newer version)
        assert is_compatible is True
        assert error_msg == ""

    def test_no_version_in_metadata(self):
        """Test validation when metadata has no version info."""
        metadata = ArtifactMetadata(schema_version=3)

        is_compatible, error_msg = _validate_dspy_version_compatibility(metadata)

        # Should allow but warn
        assert is_compatible is True
        assert error_msg == ""


class TestLoadRequiredCompiledModulesPhase3:
    """Tests for Phase 3 enhancements to load_required_compiled_modules."""

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    @patch("agentic_fleet.dspy_modules.compiled_registry._resolve_artifact_path")
    @patch("agentic_fleet.dspy_modules.compiled_registry._load_artifact_metadata")
    @patch("agentic_fleet.dspy_modules.compiled_registry._validate_dspy_version_compatibility")
    def test_load_with_incompatible_artifact_strict_mode(
        self, mock_validate, mock_load_meta, mock_resolve, mock_load
    ):
        """Test that incompatible artifacts fail in strict mode."""
        # Mock path resolution
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_resolve.return_value = mock_path

        # Mock metadata with incompatible version
        metadata = ArtifactMetadata(schema_version=3, dspy_version="2.0.0")
        mock_load_meta.return_value = metadata
        mock_validate.return_value = (False, "Version too old")

        # Mock module loading
        mock_load.return_value = MagicMock()

        dspy_config = {
            "compiled_routing_path": "/test/routing.json",
            "compiled_tool_planning_path": "/test/tool_planning.json",
            "compiled_quality_path": "/test/quality.pkl",
        }

        # Should raise RuntimeError with incompatible artifacts
        with pytest.raises(RuntimeError) as exc_info:
            load_required_compiled_modules(
                dspy_config=dspy_config,
                require_compiled=True,
            )

        error_msg = str(exc_info.value)
        assert "Incompatible artifacts" in error_msg

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    @patch("agentic_fleet.dspy_modules.compiled_registry._resolve_artifact_path")
    @patch("agentic_fleet.dspy_modules.compiled_registry._load_artifact_metadata")
    @patch("agentic_fleet.dspy_modules.compiled_registry._validate_dspy_version_compatibility")
    def test_load_with_valid_metadata(self, mock_validate, mock_load_meta, mock_resolve, mock_load):
        """Test successful loading with valid metadata."""
        # Mock path resolution
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_resolve.return_value = mock_path

        # Mock metadata with compatible version
        metadata = ArtifactMetadata(schema_version=3, dspy_version="3.0.5")
        mock_load_meta.return_value = metadata
        mock_validate.return_value = (True, "")

        # Mock module loading
        mock_module = MagicMock()
        mock_load.return_value = mock_module

        dspy_config = {
            "compiled_routing_path": "/test/routing.json",
            "compiled_tool_planning_path": "/test/tool_planning.json",
            "compiled_quality_path": "/test/quality.pkl",
        }

        registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=True,
        )

        assert registry is not None
        assert registry.routing is mock_module
        assert registry.tool_planning is mock_module
        assert registry.quality is mock_module
