"""
ApiKey model
Flow: API key management for flow deployment
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .user import User


class ApiKey(Base):
    """ApiKey model - represents API keys for accessing deployed flows."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Key metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # The actual API key (hashed)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Key prefix for identification (first 8 chars, unhashed)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_count: Mapped[int] = mapped_column(default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, user_id={self.user_id})>"