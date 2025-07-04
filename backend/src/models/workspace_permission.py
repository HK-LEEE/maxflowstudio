"""
Workspace Permission model
Flow: User/Group -> Workspace -> Permission level
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, func, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .workspace import Workspace


class PermissionType(str, Enum):
    """Permission type enumeration."""
    OWNER = "owner"     # Full control including delete
    ADMIN = "admin"     # Manage members and flows  
    MEMBER = "member"   # Create and edit flows
    VIEWER = "viewer"   # Read-only access


class WorkspacePermission(Base):
    """WorkspacePermission model - manages user/group permissions for workspaces."""
    
    __tablename__ = "workspace_permissions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Workspace reference
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # User permission (for individual users)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE")
    )
    
    # Group permission (for groups)
    group_id: Mapped[str | None] = mapped_column(String(100))
    
    # Permission level
    permission_type: Mapped[PermissionType] = mapped_column(
        SQLEnum(PermissionType),
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
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="permissions"
    )
    user: Mapped["User | None"] = relationship("User")
    
    # Constraints
    __table_args__ = (
        # Ensure either user_id or group_id is set, but not both
        UniqueConstraint("workspace_id", "user_id", name="unique_workspace_user_permission"),
        UniqueConstraint("workspace_id", "group_id", name="unique_workspace_group_permission"),
    )
    
    def __repr__(self) -> str:
        target = f"user:{self.user_id}" if self.user_id else f"group:{self.group_id}"
        return f"<WorkspacePermission(workspace_id={self.workspace_id}, {target}, permission={self.permission_type})>"