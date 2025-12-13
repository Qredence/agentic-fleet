"""Compiled DSPy artifact registry with fail-fast enforcement.

This module provides centralized loading and validation of compiled DSPy modules.
In production environments, all required compiled artifacts must exist at startup.
Missing artifacts will cause FastAPI lifespan to fail-fast, preventing degraded
performance from zero-shot fallback behavior.

Phase 1 Goals:
- Enforce that required compiled artifacts exist at startup
- Fail-fast in FastAPI lifespan instead of warning/falling back
- Support typed, independently-loadable DSPy decision modules
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompiledArtifact:
    """Metadata for a compiled DSPy artifact."""

    name: str
    path: Path
    required: bool
    description: str
    module: Any | None = None


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
            return candidate

    # Return the path relative to repo root if not found
    return (bases[0] / path).resolve()


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
            "DSPy is required for compiled module loading. "
            "Install with: pip install dspy-ai>=3.0.3"
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
                dspy_config.get(
                    "compiled_quality_path", ".var/logs/compiled_answer_quality.pkl"
                )
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

        try:
            module = load_compiled_module(str(artifact.path))
            if module is not None:
                artifact.module = module
                setattr(registry, artifact.name, module)
                logger.info("Successfully loaded compiled artifact: %s", artifact.name)
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

    # Fail-fast if required artifacts are missing
    if missing_required:
        missing_names = [a.name for a in missing_required]
        missing_paths = [str(a.path) for a in missing_required]
        raise RuntimeError(
            f"Required compiled DSPy artifacts not found: {missing_names}\n"
            f"Paths checked: {missing_paths}\n\n"
            "To fix this:\n"
            "1. Run 'agentic-fleet optimize' to compile DSPy modules\n"
            "2. Or set 'dspy.require_compiled: false' in workflow_config.yaml "
            "to allow zero-shot fallback (not recommended for production)\n\n"
            "DSPy compilation is mandatory in production to ensure consistent, "
            "high-quality outputs. Zero-shot fallback degrades performance significantly."
        )

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
    "ArtifactRegistry",
    "CompiledArtifact",
    "load_required_compiled_modules",
    "validate_artifact_registry",
]
