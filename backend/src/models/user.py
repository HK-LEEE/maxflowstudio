"""
User model
Flow: User data from auth server -> Local user reference
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .flow import Flow
    from .api_key import ApiKey
    from .environment_variable import EnvironmentVariable


class User(Base):
    """User model - references users from auth server."""
    
    __tablename__ = "users"
    
    # User ID from auth server (UUID string)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    
    # Group membership (from auth server)
    group_id: Mapped[str | None] = mapped_column(String(100))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    flows: Mapped[list["Flow"]] = relationship(
        "Flow", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    environment_variables: Mapped[list["EnvironmentVariable"]] = relationship(
        "EnvironmentVariable",
        foreign_keys="EnvironmentVariable.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"