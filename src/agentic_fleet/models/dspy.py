"""DSPy-specific models for the AgenticFleet API.

Defines models for DSPy compilation, caching, and optimization operations.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CompileRequest(BaseModel):
    """Request to compile/optimize DSPy module.

    Attributes:
        optimizer: Optimization strategy to use.
        use_cache: Whether to use cached compilation if available.
        gepa_auto: GEPA preset configuration (light, medium, heavy).
        harvest_history: Whether to harvest examples from execution history.
        min_quality: Minimum quality score for harvested examples.
    """

    optimizer: Literal["bootstrap", "gepa"] = Field(default="bootstrap")
    use_cache: bool = Field(default=True)
    gepa_auto: Literal["light", "medium", "heavy"] | None = Field(default="light")
    harvest_history: bool = Field(default=False)
    min_quality: float = Field(default=8.0, ge=0, le=10)


class CompileResponse(BaseModel):
    """Response from compilation operation.

    Attributes:
        status: Compilation status.
        job_id: Background job ID if compilation was started asynchronously.
        message: Human-readable status message.
        cache_path: Path to cache file if applicable.
    """

    status: Literal["started", "completed", "cached", "failed"]
    job_id: str | None = Field(default=None)
    message: str
    cache_path: str | None = Field(default=None)


class OptimizationJobStatus(BaseModel):
    """Status for a background optimization job started via the API."""

    status: Literal["started", "running", "completed", "cached", "failed"]
    job_id: str | None = Field(default=None)
    message: str
    cache_path: str | None = Field(default=None)
    started_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)
    error: str | None = Field(default=None)
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    details: dict[str, object] | None = Field(default=None)


class SelfImproveRequest(BaseModel):
    """Request to trigger self-improvement from execution history."""

    min_quality: float = Field(default=8.0, ge=0, le=10)
    max_examples: int = Field(default=20, ge=1, le=200)
    stats_only: bool = Field(default=False)


class SelfImproveResponse(BaseModel):
    """Response from self-improvement."""

    status: Literal["completed", "no_op", "failed"]
    message: str
    new_examples_added: int = Field(default=0, ge=0)
    stats: dict[str, object] | None = Field(default=None)


class CacheInfo(BaseModel):
    """Information about DSPy compilation cache.

    Attributes:
        exists: Whether a cache file exists.
        created_at: Cache creation timestamp.
        cache_size_bytes: Size of cache file in bytes.
        optimizer: Optimizer used for this cache.
        signature_hash: Hash of signatures used in compilation.
    """

    exists: bool
    created_at: str | None = Field(default=None)
    cache_size_bytes: int | None = Field(default=None)
    optimizer: str | None = Field(default=None)
    signature_hash: str | None = Field(default=None)


class ReasonerSummary(BaseModel):
    """Summary of DSPy reasoner state.

    Attributes:
        history_count: Number of history entries.
        routing_cache_size: Size of routing decision cache.
        use_typed_signatures: Whether typed signatures are enabled.
        modules_initialized: Whether DSPy modules are initialized.
    """

    history_count: int
    routing_cache_size: int
    use_typed_signatures: bool
    modules_initialized: bool = False


class SignatureInfo(BaseModel):
    """Information about a DSPy signature.

    Attributes:
        name: Signature name.
        type: Signature type.
        instructions: Signature instructions.
        input_fields: List of input field names.
        output_fields: List of output field names.
    """

    name: str
    type: str
    instructions: str | None = Field(default=None)
    input_fields: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
