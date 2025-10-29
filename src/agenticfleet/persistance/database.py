import enum
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, DateTime, String, create_engine
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Align with existing var/ structure used by other components
DATABASE_PATH = Path("var") / "agenticfleet" / "approvals.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base: Any = declarative_base()


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest(Base):  # type: ignore[misc]
    __tablename__ = "approval_requests"

    request_id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, index=True)
    status = Column(SQLAlchemyEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Any:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
