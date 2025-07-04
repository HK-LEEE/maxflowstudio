"""
Workspace model
Flow: Workspace -> Flow mapping -> Permission management
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .workspace_permission import WorkspacePermission
    from .flow_workspace_map import FlowWorkspaceMap
    from .environment_variable import EnvironmentVariable
    from .workspace_mapping import WorkspaceUserMapping, WorkspaceGroupMapping
    from .rag_collection import RAGCollection


class WorkspaceType(str, Enum):
    """Workspace type enumeration."""
    USER = "user"       # Personal workspace
    GROUP = "group"     # Group workspace


class Workspace(Base):
    """Workspace model - represents a workspace for organizing flows."""
    
    __tablename__ = "workspaces"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Workspace type
    type: Mapped[WorkspaceType] = mapped_column(
        SQLEnum(WorkspaceType),
        default=WorkspaceType.USER
    )
    
    # Creator information
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Group association (for group workspaces)
    group_id: Mapped[str | None] = mapped_column(String(100))
    
    # Workspace settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
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
    creator: Mapped["User"] = relationship("User")
    permissions: Mapped[list["WorkspacePermission"]] = relationship(
        "WorkspacePermission",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    flow_mappings: Mapped[list["FlowWorkspaceMap"]] = relationship(
        "FlowWorkspaceMap",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    environment_variables: Mapped[list["EnvironmentVariable"]] = relationship(
        "EnvironmentVariable",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    user_mappings: Mapped[list["WorkspaceUserMapping"]] = relationship(
        "WorkspaceUserMapping",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    group_mappings: Mapped[list["WorkspaceGroupMapping"]] = relationship(
        "WorkspaceGroupMapping", 
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    rag_collections: Mapped[list["RAGCollection"]] = relationship(
        "RAGCollection",
        back_populates="workspace",
        cascade="all, delete-orphan",
        order_by="RAGCollection.created_at.desc()"
    )
    
    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name}, type={self.type})>"