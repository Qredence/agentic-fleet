"""Azure Cosmos DB helpers for AgenticFleet.

This module centralizes optional Cosmos DB integration so that:
- Cosmos usage is enabled/disabled purely via environment variables.
- Runtime behaviour degrades gracefully when Cosmos is misconfigured or
  unavailable (no exceptions are raised in the main execution path).

Current responsibilities:
- Detect whether Cosmos integration is enabled.
- Create and cache a shared ``CosmosClient`` instance.
- Provide a helper to mirror execution history into the ``workflowRuns``
  container when available.

The actual database and containers are expected to be provisioned ahead
of time (for example via the Azure CLI). This module does **not** create
resources automatically; this avoids surprises around throughput and
account modes (e.g. serverless).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import CosmosClientProtocol

try:
    from azure.cosmos import CosmosClient, exceptions  # type: ignore[import]
    from azure.identity import DefaultAzureCredential  # type: ignore[import]

    _HAS_COSMOS_SDK = True
except ImportError:
    _HAS_COSMOS_SDK = False
    CosmosClient = None  # type: ignore[misc,assignment]
    exceptions = None  # type: ignore[misc,assignment]
    DefaultAzureCredential = None  # type: ignore[misc,assignment]

from .logger import setup_logger

logger = setup_logger(__name__)

# Cached singleton client to avoid re-creating connections.
_COSMOS_CLIENT: CosmosClientProtocol | None = None
_MISSING_USER_ID_WARNING_EMITTED = False


def _bool_env(name: str) -> bool:
    """Return True if the environment variable is a truthy value.

    Truthy values (case-insensitive): ``{"1", "true", "yes", "on"}``.
    """

    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_cosmos_enabled() -> bool:
    """
    Indicates if Cosmos integration is enabled via the AGENTICFLEET_USE_COSMOS environment variable.

    Returns:
        true if the environment variable represents a truthy value (1, "true", "yes", "on"), false otherwise.
    """

    return _bool_env("AGENTICFLEET_USE_COSMOS")


def _get_cosmos_client() -> CosmosClientProtocol | None:
    """Create (or return cached) CosmosClient if configuration is valid.

    Returns ``None`` if Cosmos integration is disabled or misconfigured.
    """

    global _COSMOS_CLIENT

    if _COSMOS_CLIENT is not None:
        return _COSMOS_CLIENT

    if not is_cosmos_enabled():
        return None

    endpoint = os.getenv("AZURE_COSMOS_ENDPOINT", "").strip()
    if not endpoint:
        logger.warning(
            "Cosmos integration enabled but AZURE_COSMOS_ENDPOINT is not set; "
            "skipping Cosmos client creation.",
        )
        return None

    use_managed_identity = _bool_env("AZURE_COSMOS_USE_MANAGED_IDENTITY")

    try:
        if use_managed_identity:
            if DefaultAzureCredential is None:
                logger.error("DefaultAzureCredential not available - azure-identity not installed")
                return None
            credential = DefaultAzureCredential()
            if CosmosClient is None:
                logger.error("CosmosClient not available - azure-cosmos not installed")
                return None
            client = CosmosClient(endpoint, credential=credential)
            logger.info("CosmosClient created using managed identity.")
        else:
            key = os.getenv("AZURE_COSMOS_KEY", "").strip()
            if not key:
                logger.warning(
                    "Cosmos integration enabled but AZURE_COSMOS_KEY is not set "
                    "and managed identity is disabled; skipping Cosmos client.",
                )
                return None
            if CosmosClient is None:
                logger.error("CosmosClient not available - azure-cosmos not installed")
                return None
            client = CosmosClient(endpoint, credential=key)
            logger.info("CosmosClient created using key-based credentials.")

        _COSMOS_CLIENT = client
        return client

    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            "Failed to create CosmosClient; disabling Cosmos integration. Error: %s",
            exc,
            exc_info=True,
        )
        return None


def _get_database():
    """Return database client for ``AZURE_COSMOS_DATABASE`` or None.

    The database is expected to exist already.
    """

    client = _get_cosmos_client()
    if client is None:
        return None

    database_id = os.getenv("AZURE_COSMOS_DATABASE", "").strip()
    if not database_id:
        logger.warning(
            "Cosmos integration enabled but AZURE_COSMOS_DATABASE is not set; "
            "skipping Cosmos history mirror.",
        )
        return None

    try:
        return client.get_database_client(database_id)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning("Failed to get Cosmos database '%s': %s", database_id, exc, exc_info=True)
        return None
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            "Unexpected error while getting Cosmos database '%s': %s",
            database_id,
            exc,
            exc_info=True,
        )
        return None


def _get_container(env_var: str, default_id: str):
    """Return container client using env override with graceful fallbacks."""

    database = _get_database()
    if database is None:
        return None

    container_id = os.getenv(env_var, default_id).strip()
    if not container_id:
        logger.warning(
            "%s is empty; skipping Cosmos container lookup.",
            env_var,
        )
        return None

    try:
        return database.get_container_client(container_id)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning(
            "Failed to get Cosmos container '%s': %s",
            container_id,
            exc,
            exc_info=True,
        )
        return None
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            "Unexpected error while getting Cosmos container '%s': %s",
            container_id,
            exc,
            exc_info=True,
        )
        return None


def _get_history_container():
    """Return container client for workflow run history, or None.

    Uses ``AZURE_COSMOS_WORKFLOW_RUNS_CONTAINER`` with default ``workflowRuns``.
    """

    return _get_container("AZURE_COSMOS_WORKFLOW_RUNS_CONTAINER", "workflowRuns")


def _get_agent_memory_container():
    return _get_container("AZURE_COSMOS_AGENT_MEMORY_CONTAINER", "agentMemory")


def _get_dspy_examples_container():
    return _get_container("AZURE_COSMOS_DSPY_EXAMPLES_CONTAINER", "dspyExamples")


def _get_dspy_optimization_runs_container():
    return _get_container("AZURE_COSMOS_DSPY_OPTIMIZATION_RUNS_CONTAINER", "dspyOptimizationRuns")


def _get_cache_container():
    return _get_container("AZURE_COSMOS_CACHE_CONTAINER", "cache")


def get_default_user_id() -> str | None:
    """Return the default user/tenant identifier for partitioning."""

    for env_name in (
        "AGENTICFLEET_DEFAULT_USER_ID",
        "AGENTICFLEET_USER_ID",
        "USER",
        "USERNAME",
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return None


def _sanitize_for_cosmos(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable formats."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return _sanitize_for_cosmos(obj.to_dict())
    if isinstance(obj, dict):
        return {k: _sanitize_for_cosmos(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_sanitize_for_cosmos(i) for i in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


def mirror_execution_history(execution: dict[str, Any]) -> None:
    """Mirror a single execution record into Cosmos ``workflowRuns`` container.

    This helper is intentionally best-effort:
    - If Cosmos is disabled or misconfigured, it returns silently.
    - If any Cosmos call fails, it logs a warning and returns.

    Args:
        execution: Execution dictionary as produced by the workflow adapter.
    """

    if not is_cosmos_enabled():
        return

    container = _get_history_container()
    if container is None:
        return

    # Create a shallow copy so we do not mutate the caller's structure.
    # And sanitize for JSON serialization (e.g. RoutingDecision objects)
    item: dict[str, Any] = _sanitize_for_cosmos(execution)

    # Ensure we have a stable workflowId and id for Cosmos.
    workflow_id = item.get("workflowId")
    if not workflow_id:
        workflow_id = str(uuid.uuid4())
        item["workflowId"] = workflow_id

    item.setdefault("id", workflow_id)
    item.setdefault("createdAt", datetime.now(UTC).isoformat())

    # Best-effort tenant scoping: attach a userId when available so callers can
    # filter history without exposing other users' runs.
    if not item.get("userId"):
        default_user_id = get_default_user_id()
        if default_user_id:
            item["userId"] = default_user_id

    try:
        # Partition key path for the container is /workflowId.
        container.upsert_item(body=item)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning(
            "Failed to mirror execution to Cosmos (HTTP error); continuing without "
            "cloud history. Error: %s",
            exc,
            exc_info=True,
        )
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            "Failed to mirror execution to Cosmos; continuing without cloud history. Error: %s",
            exc,
            exc_info=True,
        )


def save_agent_memory_item(item: dict[str, Any], *, user_id: str | None = None) -> None:
    """Persist a long-term agent memory item in Cosmos."""

    if not is_cosmos_enabled():
        return

    container = _get_agent_memory_container()
    if container is None:
        return

    doc = dict(item)
    resolved_user_id = user_id or doc.get("userId") or get_default_user_id()
    if not resolved_user_id:
        global _MISSING_USER_ID_WARNING_EMITTED
        if not _MISSING_USER_ID_WARNING_EMITTED:
            logger.debug(
                "Skipping agent memory write: no userId available (set AGENTICFLEET_DEFAULT_USER_ID)."
            )
            _MISSING_USER_ID_WARNING_EMITTED = True
        return

    doc["userId"] = resolved_user_id
    memory_id = doc.get("memoryId") or doc.get("id") or str(uuid.uuid4())
    doc["memoryId"] = memory_id
    doc.setdefault("content", doc.get("text") or doc.get("summary") or "")
    doc["id"] = doc.get("id", memory_id)
    now = datetime.now(UTC).isoformat()
    doc.setdefault("createdAt", now)
    doc["updatedAt"] = now

    try:
        container.upsert_item(doc)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning("Failed to save agent memory: %s", exc, exc_info=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Unexpected error while saving agent memory: %s", exc, exc_info=True)


def query_agent_memory(
    *,
    user_id: str,
    agent_id: str | None = None,
    memory_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch memory items for a user with optional filters."""

    if not is_cosmos_enabled() or not user_id:
        return []

    container = _get_agent_memory_container()
    if container is None:
        return []

    query = "SELECT TOP @limit * FROM c WHERE c.userId = @userId"
    parameters: list[dict[str, Any]] = [
        {"name": "@userId", "value": user_id},
        {"name": "@limit", "value": limit},
    ]

    if agent_id:
        query += " AND c.agentId = @agentId"
        parameters.append({"name": "@agentId", "value": agent_id})
    if memory_type:
        query += " AND c.memoryType = @memoryType"
        parameters.append({"name": "@memoryType", "value": memory_type})

    query += " ORDER BY c.createdAt DESC"

    try:
        items = container.query_items(
            query=query,
            parameters=parameters,
            partition_key=user_id,
            enable_cross_partition_query=False,
        )
        return list(items)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning("Failed to query agent memory: %s", exc, exc_info=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Unexpected error while querying agent memory: %s", exc, exc_info=True)
    return []


def mirror_dspy_examples(
    examples: Iterable[dict[str, Any]],
    *,
    user_id: str | None = None,
    dataset: str = "supervisor_routing_examples",
) -> None:
    """Best-effort mirror of DSPy routing examples to Cosmos."""

    if not is_cosmos_enabled():
        return

    container = _get_dspy_examples_container()
    if container is None:
        return

    resolved_user_id = user_id or get_default_user_id()
    if not resolved_user_id:
        logger.debug("Skipping DSPy example mirror: no userId configured.")
        return

    now = datetime.now(UTC).isoformat()
    for example in examples:
        doc = dict(example)
        example_id = doc.get("exampleId") or doc.get("id") or str(uuid.uuid4())
        doc["exampleId"] = example_id
        doc["id"] = doc.get("id", example_id)
        doc["userId"] = resolved_user_id
        doc.setdefault("dataset", dataset)
        doc.setdefault("createdAt", now)

        try:
            container.upsert_item(doc)
        except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
            logger.debug("Failed to mirror DSPy example: %s", exc)
        except Exception as exc:  # pragma: no cover
            logger.debug("Unexpected error mirroring DSPy example: %s", exc)


def record_dspy_optimization_run(
    run: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
    """Persist GEPA/optimization run metadata for auditing."""

    if not is_cosmos_enabled():
        return

    container = _get_dspy_optimization_runs_container()
    if container is None:
        return

    resolved_user_id = user_id or run.get("userId") or get_default_user_id()
    if not resolved_user_id:
        logger.debug("Skipping optimization run mirror: no userId configured.")
        return

    doc = dict(run)
    run_id = doc.get("runId") or doc.get("id") or str(uuid.uuid4())
    doc["runId"] = run_id
    doc["id"] = doc.get("id", run_id)
    doc["userId"] = resolved_user_id
    doc.setdefault("createdAt", datetime.now(UTC).isoformat())

    try:
        container.upsert_item(doc)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.debug("Failed to record optimization run: %s", exc)
    except Exception as exc:  # pragma: no cover
        logger.debug("Unexpected error recording optimization run: %s", exc)


def mirror_cache_entry(cache_key: str, entry: dict[str, Any]) -> None:
    """Mirror cache metadata into Cosmos for analytics/debugging."""

    if not is_cosmos_enabled():
        return

    container = _get_cache_container()
    if container is None:
        return

    doc = dict(entry)
    doc["cacheKey"] = cache_key
    # Align with the documented cache container semantics: stable id per cacheKey.
    # If callers want append-only analytics, they can provide their own id.
    doc.setdefault("id", cache_key)
    doc.setdefault("createdAt", datetime.now(UTC).isoformat())
    doc["updatedAt"] = datetime.now(UTC).isoformat()

    # Optional: per-item TTL (seconds). This is only applied if the container has TTL enabled.
    ttl_seconds = doc.get("ttl")
    if ttl_seconds is None:
        ttl_seconds = doc.get("ttlSeconds")
    if isinstance(ttl_seconds, int):
        doc.setdefault("ttl", ttl_seconds)

    try:
        container.upsert_item(doc)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.debug("Failed to mirror cache entry: %s", exc)
    except Exception as exc:  # pragma: no cover
        logger.debug("Unexpected error mirroring cache entry: %s", exc)


def load_execution_history(limit: int = 20, *, user_id: str | None = None) -> list[dict[str, Any]]:
    """Load execution history from Cosmos DB.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of execution dictionaries
    """
    if not is_cosmos_enabled():
        return []

    container = _get_history_container()
    if container is None:
        return []

    if user_id:
        query = "SELECT TOP @limit * FROM c WHERE c.userId = @userId ORDER BY c.createdAt DESC"
        parameters = [
            {"name": "@userId", "value": user_id},
            {"name": "@limit", "value": limit},
        ]
    else:
        query = "SELECT TOP @limit * FROM c ORDER BY c.createdAt DESC"
        parameters = [{"name": "@limit", "value": limit}]

    try:
        items = container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        )
        return list(items)
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning("Failed to load execution history: %s", exc, exc_info=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Unexpected error while loading execution history: %s", exc, exc_info=True)
    return []


def get_execution(workflow_id: str) -> dict[str, Any] | None:
    """Retrieve a specific execution by ID from Cosmos DB.

    Args:
        workflow_id: The workflow ID to retrieve

    Returns:
        Execution dictionary or None if not found
    """
    if not is_cosmos_enabled():
        return None

    container = _get_history_container()
    if container is None:
        return None

    try:
        # Read item directly by ID and partition key (workflowId)
        # Note: We assume partition key is workflowId as per mirror_execution_history
        item = container.read_item(item=workflow_id, partition_key=workflow_id)
        return item
    except exceptions.CosmosResourceNotFoundError:  # type: ignore[attr-defined]
        return None
    except exceptions.CosmosHttpResponseError as exc:  # type: ignore[attr-defined]
        logger.warning("Failed to get execution %s: %s", workflow_id, exc, exc_info=True)
        return None
    except Exception as exc:  # pragma: no cover
        logger.warning("Unexpected error getting execution %s: %s", workflow_id, exc, exc_info=True)
        return None


__all__ = [
    "get_default_user_id",
    "get_execution",
    "is_cosmos_enabled",
    "load_execution_history",
    "mirror_cache_entry",
    "mirror_dspy_examples",
    "mirror_execution_history",
    "query_agent_memory",
    "record_dspy_optimization_run",
    "save_agent_memory_item",
]
