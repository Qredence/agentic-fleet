"""Compiled DSPy artifact registry with fail-fast enforcement.

This module provides centralized loading and validation of compiled DSPy modules.
In production environments, all required compiled artifacts must exist at startup.
Missing artifacts will cause FastAPI lifespan to fail-fast, preventing degraded
performance from zero-shot fallback behavior.

Phase 1 Goals:
- Enforce that required compiled artifacts exist at startup
- Fail-fast in FastAPI lifespan instead of warning/falling back
- Support typed, independently-loadable DSPy decision modules

Phase 3 Goals:
- Add artifact metadata and compatibility checks
- Validate schema version, DSPy version compatibility
- Provide actionable error messages with resolution steps
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Minimum required DSPy version
MIN_DSPY_VERSION = "3.0.3"


@dataclass
class ArtifactMetadata:
    """Metadata for compiled artifact validation.

    Phase 3: Extended metadata for compatibility checking.
    """

    schema_version: int
    """Schema version of the artifact format"""

    dspy_version: str | None = None
    """DSPy version used for compilation"""

    created_at: str | None = None
    """Timestamp when artifact was created"""

    optimizer: str | None = None
    """Optimizer used for compilation"""

    build_id: str | None = None
    """Optional build/commit identifier"""

    serializer: str | None = None
    """Serialization method used"""


@dataclass
class CompiledArtifact:
    """Metadata for a compiled DSPy artifact."""

    name: str
    path: Path
    required: bool
    description: str
    module: Any | None = None
    metadata: ArtifactMetadata | None = None


@dataclass
class ArtifactRegistry:
    """Registry holding all loaded compiled DSPy modules."""

    routing: Any | None = None
    tool_planning: Any | None = None
    quality: Any | None = None
    reasoner: Any | None = None

    def get_module(self, name: str) -> Any | None:
        """Get a loaded module by name."""
        return getattr(self, name, None)


def _search_bases() -> list[Path]:
    """Search for candidate base directories to resolve relative paths."""
    resolved = Path(__file__).resolve()
    parents = resolved.parents
    repo_root = parents[3] if len(parents) > 3 else parents[-1]
    package_root = parents[1] if len(parents) > 1 else parents[-1]
    module_dir = resolved.parent
    return [repo_root, package_root, module_dir, Path.cwd()]


def _resolve_artifact_path(relative_path: str | Path) -> Path:
    """Resolve a relative artifact path to an absolute path.

    Searches multiple base directories in order:
    1. Repository root
    2. Package root
    3. Module directory
    4. Current working directory

    Args:
        relative_path: Relative path to the artifact

    Returns:
        Resolved absolute path (may not exist)
    """
    path = Path(relative_path).expanduser()
    if path.is_absolute():
        return path

    bases = _search_bases()
    for base in bases:
        candidate = (base / path).resolve()
        if candidate.exists():
            logger.debug("Resolved artifact path: %s -> %s", relative_path, candidate)
            return candidate

    # Return the path relative to repo root if not found
    resolved = (bases[0] / path).resolve()
    logger.debug("Artifact path (not found): %s -> %s", relative_path, resolved)
    return resolved


def _load_artifact_metadata(path: Path) -> ArtifactMetadata | None:
    """Load metadata from artifact file.

    Phase 3: Extract metadata for compatibility validation.

    Args:
        path: Path to artifact file

    Returns:
        ArtifactMetadata if found, None otherwise
    """
    metadata_path = Path(str(path) + ".meta")
    if not metadata_path.exists():
        logger.debug("No metadata file found at %s", metadata_path)
        return None

    try:
        with open(metadata_path) as f:
            data = json.load(f)

        # Extract relevant fields
        metadata = ArtifactMetadata(
            schema_version=data.get("version", 0),
            dspy_version=data.get("dspy_version"),
            created_at=data.get("created_at"),
            optimizer=data.get("optimizer"),
            build_id=data.get("build_id"),
            serializer=data.get("serializer"),
        )
        logger.debug("Loaded metadata for %s: schema_version=%s", path, metadata.schema_version)
        return metadata
    except Exception as e:
        logger.warning("Failed to load metadata from %s: %s", metadata_path, e)
        return None


def _validate_dspy_version_compatibility(metadata: ArtifactMetadata) -> tuple[bool, str]:
    """Validate DSPy version compatibility.

    Phase 3: Ensure compiled artifacts are compatible with current DSPy version.

    Args:
        metadata: Artifact metadata

    Returns:
        Tuple of (is_compatible, error_message)
    """
    if not metadata.dspy_version:
        # No version info - allow but warn
        return True, ""

    try:
        import dspy
        from packaging.version import InvalidVersion, Version

        current_version = getattr(dspy, "__version__", "unknown")

        # Parse versions for comparison.
        # NOTE: DSPy frequently publishes prerelease versions like `3.1.0b1`.
        # A naive `split('.')`+`int()` parser will treat these as invalid and
        # incorrectly mark them as (0, 0, 0). Use PEP 440 parsing instead.
        def parse_version(v: str) -> Version:
            try:
                return Version(v)
            except InvalidVersion:
                logger.error("Invalid version string encountered: '%s'.", v)
                raise

        try:
            current = parse_version(current_version)
            required = parse_version(MIN_DSPY_VERSION)
            artifact = parse_version(metadata.dspy_version)
        except InvalidVersion as e:
            return False, (
                f"Invalid version string encountered during DSPy version compatibility check: {e}. "
                "Artifact or environment version is malformed. Please check your installation and artifact metadata."
            )

        # Check if current version meets minimum
        if current < required:
            return False, (
                f"Current DSPy version {current_version} is below minimum required {MIN_DSPY_VERSION}. "
                f"Upgrade with: pip install 'dspy-ai>={MIN_DSPY_VERSION}'"
            )

        # Warn if artifact compiled with different version
        if artifact != current:
            logger.warning(
                "Artifact compiled with DSPy %s, running with %s. "
                "Consider recompiling if you encounter issues.",
                metadata.dspy_version,
                current_version,
            )

        return True, ""

    except ImportError:
        return False, "DSPy is not installed"
    except Exception as e:
        logger.warning("Failed to validate DSPy version: %s", e)
        return True, ""  # Allow to proceed on validation failure


def load_required_compiled_modules(
    dspy_config: dict[str, Any],
    require_compiled: bool = True,
) -> ArtifactRegistry:
    """Load required compiled DSPy modules with fail-fast enforcement.

    This function is called during FastAPI lifespan startup to preload all
    required compiled DSPy artifacts. If `require_compiled` is True and any
    required artifact is missing, this function raises RuntimeError to fail-fast.

    Args:
        dspy_config: DSPy configuration dictionary from workflow_config.yaml
        require_compiled: If True, raise error on missing artifacts (production mode)

    Returns:
        ArtifactRegistry with loaded modules

    Raises:
        RuntimeError: If required artifacts are missing and require_compiled=True
        ImportError: If DSPy is not installed
    """
    # Import here to avoid circular imports and handle missing DSPy gracefully
    try:
        import dspy  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "DSPy is required for compiled module loading. Install with: pip install dspy-ai>=3.0.3"
        ) from e

    from ..utils.compiler import load_compiled_module

    # Define required artifacts with their config keys
    artifacts = [
        CompiledArtifact(
            name="routing",
            path=_resolve_artifact_path(
                dspy_config.get("compiled_routing_path", ".var/cache/dspy/compiled_routing.json")
            ),
            required=require_compiled,
            description="Routing decision module for task assignment",
        ),
        CompiledArtifact(
            name="tool_planning",
            path=_resolve_artifact_path(
                dspy_config.get(
                    "compiled_tool_planning_path", ".var/cache/dspy/compiled_tool_planning.json"
                )
            ),
            required=require_compiled,
            description="Tool planning module for tool selection",
        ),
        CompiledArtifact(
            name="quality",
            path=_resolve_artifact_path(
                dspy_config.get("compiled_quality_path", ".var/logs/compiled_answer_quality.pkl")
            ),
            required=require_compiled,
            description="Quality assessment module for answer scoring",
        ),
        CompiledArtifact(
            name="reasoner",
            path=_resolve_artifact_path(
                dspy_config.get("compiled_reasoner_path", ".var/cache/dspy/compiled_reasoner.json")
            ),
            required=False,  # Reasoner is optional (has zero-shot fallback in initialization)
            description="Main reasoner module (optional, has fallback)",
        ),
    ]

    registry = ArtifactRegistry()
    missing_required = []
    incompatible_artifacts = []

    # Phase 3: Log all resolved artifact paths at startup
    logger.info("=== DSPy Artifact Registry Startup ===")
    logger.info("require_compiled: %s", require_compiled)
    for artifact in artifacts:
        logger.info(
            "  %s: %s (required=%s)",
            artifact.name,
            artifact.path,
            artifact.required,
        )
    logger.info("=" * 40)

    for artifact in artifacts:
        logger.info(
            "Loading compiled artifact: %s from %s (required=%s)",
            artifact.name,
            artifact.path,
            artifact.required,
        )

        if not artifact.path.exists():
            if artifact.required:
                missing_required.append(artifact)
                logger.error(
                    "Required compiled artifact not found: %s at %s",
                    artifact.name,
                    artifact.path,
                )
            else:
                logger.warning(
                    "Optional compiled artifact not found: %s at %s (will use fallback)",
                    artifact.name,
                    artifact.path,
                )
            continue

        # Phase 3: Load and validate metadata
        metadata = _load_artifact_metadata(artifact.path)
        if metadata:
            artifact.metadata = metadata

            # Validate DSPy version compatibility
            is_compatible, error_msg = _validate_dspy_version_compatibility(metadata)
            if not is_compatible:
                if artifact.required and require_compiled:
                    incompatible_artifacts.append((artifact, error_msg))
                    logger.error(
                        "Incompatible artifact %s: %s",
                        artifact.name,
                        error_msg,
                    )
                    continue
                else:
                    logger.warning(
                        "Artifact %s has compatibility issue (proceeding): %s",
                        artifact.name,
                        error_msg,
                    )

        try:
            module = load_compiled_module(str(artifact.path))
            if module is not None:
                artifact.module = module
                setattr(registry, artifact.name, module)
                logger.info(
                    "Successfully loaded compiled artifact: %s (schema_version=%s, dspy_version=%s)",
                    artifact.name,
                    metadata.schema_version if metadata else "unknown",
                    metadata.dspy_version if metadata else "unknown",
                )
            else:
                if artifact.required:
                    missing_required.append(artifact)
                    logger.error(
                        "Failed to deserialize required artifact: %s from %s",
                        artifact.name,
                        artifact.path,
                    )
                else:
                    logger.warning(
                        "Failed to deserialize optional artifact: %s from %s",
                        artifact.name,
                        artifact.path,
                    )
        except Exception as e:
            if artifact.required:
                missing_required.append(artifact)
                logger.error(
                    "Error loading required artifact %s: %s",
                    artifact.name,
                    e,
                    exc_info=True,
                )
            else:
                logger.warning(
                    "Error loading optional artifact %s: %s (will use fallback)",
                    artifact.name,
                    e,
                )

    # Phase 3: Fail-fast if required artifacts are missing or incompatible
    if missing_required or incompatible_artifacts:
        error_parts = []

        if missing_required:
            missing_names = [a.name for a in missing_required]
            missing_paths = [str(a.path) for a in missing_required]
            error_parts.append(
                f"Missing required artifacts: {missing_names}\nExpected paths: {missing_paths}"
            )

        if incompatible_artifacts:
            incompat_details = [f"  - {a.name}: {msg}" for a, msg in incompatible_artifacts]
            error_parts.append("Incompatible artifacts:\n" + "\n".join(incompat_details))

        error_message = "\n\n".join(error_parts)
        error_message += (
            "\n\n"
            "To fix this:\n"
            "1. Run 'agentic-fleet optimize' to compile DSPy modules\n"
            "2. Ensure DSPy version >= 3.0.3: pip install 'dspy-ai>=3.0.3'\n"
            "3. Or set 'dspy.require_compiled: false' in workflow_config.yaml "
            "to allow zero-shot fallback (not recommended for production)\n\n"
            "DSPy compilation is mandatory in production to ensure consistent, "
            "high-quality outputs. Zero-shot fallback degrades performance significantly."
        )

        raise RuntimeError(error_message)

    return registry


def validate_artifact_registry(registry: ArtifactRegistry) -> dict[str, bool]:
    """Validate which artifacts are loaded in the registry.

    Args:
        registry: Artifact registry to validate

    Returns:
        Dictionary mapping artifact names to their loaded status
    """
    return {
        "routing": registry.routing is not None,
        "tool_planning": registry.tool_planning is not None,
        "quality": registry.quality is not None,
        "reasoner": registry.reasoner is not None,
    }


__all__ = [
    "ArtifactMetadata",
    "ArtifactRegistry",
    "CompiledArtifact",
    "load_required_compiled_modules",
    "validate_artifact_registry",
]
