"""
Flow and FlowVersion models
Flow: Flow definition -> Versions -> Executions
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, func, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .execution import Execution


class Flow(Base):
    """Flow model - represents a workflow definition."""
    
    __tablename__ = "flows"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Current active version
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    
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
    user: Mapped["User"] = relationship("User", back_populates="flows")
    versions: Mapped[list["FlowVersion"]] = relationship(
        "FlowVersion", 
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="FlowVersion.version_number.desc()"
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", 
        back_populates="flow",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Flow(id={self.id}, name={self.name})>"


class FlowVersion(Base):
    """FlowVersion model - represents a specific version of a flow with enhanced versioning."""
    
    __tablename__ = "flow_studio_version"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flow_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_name: Mapped[str | None] = mapped_column(String(255))  # Optional custom name
    description: Mapped[str | None] = mapped_column(Text)
    
    # Flow definition as JSON
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Publishing status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(36))  # User ID
    
    # Change tracking
    change_summary: Mapped[str | None] = mapped_column(Text)
    parent_version_id: Mapped[str | None] = mapped_column(
        String(36), 
        ForeignKey("flow_studio_version.id"), 
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)  # User ID
    
    # Relationships
    flow: Mapped["Flow"] = relationship("Flow", back_populates="versions")
    parent_version: Mapped["FlowVersion | None"] = relationship(
        "FlowVersion", 
        remote_side=[id], 
        backref="child_versions"
    )
    
    def __repr__(self) -> str:
        return f"<FlowVersion(id={self.id}, flow_id={self.flow_id}, version={self.version_number}, published={self.is_published})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for the version"""
        if self.version_name:
            return f"v{self.version_number} - {self.version_name}"
        return f"v{self.version_number}"