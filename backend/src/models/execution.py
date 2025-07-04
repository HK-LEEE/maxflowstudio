"""
Execution model
Flow: Flow execution tracking and results
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, ForeignKey, func, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .flow import Flow
    from .user import User


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Execution(Base):
    """Execution model - represents a flow execution instance."""
    
    __tablename__ = "executions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Flow reference
    flow_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # User who triggered the execution
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Execution metadata
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus), 
        default=ExecutionStatus.PENDING
    )
    
    # Input data for the execution
    inputs: Mapped[dict | None] = mapped_column(JSON)
    
    # Output/result data
    outputs: Mapped[dict | None] = mapped_column(JSON)
    
    # Error information
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict | None] = mapped_column(JSON)
    
    # Execution metadata
    execution_logs: Mapped[list[dict] | None] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    flow: Mapped["Flow"] = relationship("Flow", back_populates="executions")
    user: Mapped["User"] = relationship("User")
    
    @property
    def duration(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, flow_id={self.flow_id}, status={self.status})>"