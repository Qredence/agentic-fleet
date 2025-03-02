"""
Base module for SQLAlchemy ORM models.
"""

from typing import Any

from sqlalchemy.ext.declarative import declarative_base, declared_attr


class CustomBase:
    """
    Custom base class for all SQLAlchemy models.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate __tablename__ automatically from the class name.
        """
        return cls.__name__.lower()

    # Add common columns or methods here
    id: Any
    created_at: Any
    updated_at: Any


# Create a base class for declarative models
Base = declarative_base(cls=CustomBase)
