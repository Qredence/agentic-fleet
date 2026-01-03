"""Database setup and persistence using SQLModel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, JSON
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine
import os


class RunTrace(SQLModel, table=True):
    """Persisted record of a workflow run."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
    team_id: str | None = None
    run_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON),
    )
    outputs: list[Any] | None = Field(default=None, sa_column=Column(JSON))
    trace: list[str] | None = Field(default=None, sa_column=Column(JSON))


def _build_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./fleet.db")
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, echo=False, connect_args=connect_args)


_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _build_engine()
    return _ENGINE


def create_db_and_tables() -> None:
    """Create database tables if they do not exist."""
    SQLModel.metadata.create_all(get_engine())


def save_run(
    *,
    message: str,
    outputs: list[Any],
    trace: list[str],
    team_id: str | None,
    metadata: dict[str, Any] | None,
) -> RunTrace:
    """Persist a workflow run record and return it."""
    run = RunTrace(
        message=message,
        outputs=outputs,
        trace=trace,
        team_id=team_id,
        run_metadata=metadata,
    )
    with Session(get_engine()) as session:
        session.add(run)
        session.commit()
        session.refresh(run)
    return run
