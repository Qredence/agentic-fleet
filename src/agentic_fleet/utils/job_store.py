from abc import ABC, abstractmethod
from typing import Any


class JobStore(ABC):
    """Abstract base class for job persistence."""

    @abstractmethod
    async def save_job(self, job_id: str, data: dict[str, Any]) -> None:
        """Save or update a job."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a job by ID."""
        pass

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        """Delete a job."""
        pass


class InMemoryJobStore(JobStore):
    """In-memory implementation of JobStore (for development/testing)."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    async def save_job(self, job_id: str, data: dict[str, Any]) -> None:
        self._jobs[job_id] = data

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    async def delete_job(self, job_id: str) -> None:
        if job_id in self._jobs:
            del self._jobs[job_id]
