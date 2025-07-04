"""
Flow Workspace Mapping model
Flow: Flow (1) : Workspace (1) mapping table
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .flow import Flow
    from .workspace import Workspace


class FlowWorkspaceMap(Base):
    """FlowWorkspaceMap model - manages flow to workspace mapping."""
    
    __tablename__ = "flow_studio_workspace_map"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Flow reference (1:1 mapping - each flow belongs to exactly one workspace)
    flow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # Ensures one flow can only be in one workspace
    )
    
    # Workspace reference
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False
    )
    
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
    flow: Mapped["Flow"] = relationship("Flow")
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="flow_mappings"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("flow_id", name="unique_flow_workspace"),
    )
    
    def __repr__(self) -> str:
        return f"<FlowWorkspaceMap(flow_id={self.flow_id}, workspace_id={self.workspace_id})>"