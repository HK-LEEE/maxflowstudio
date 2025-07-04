"""
Workspace Mapping Models
워크스페이스와 사용자/그룹 간의 매핑 및 권한을 관리하는 모델들
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.core.database import Base


class WorkspacePermissionLevel(PyEnum):
    """워크스페이스 권한 레벨"""
    OWNER = "owner"      # 소유자 - 모든 권한
    ADMIN = "admin"      # 관리자 - 멤버 관리, 플로우 관리
    MEMBER = "member"    # 멤버 - 플로우 생성/편집
    VIEWER = "viewer"    # 뷰어 - 읽기 전용


class WorkspaceUserMapping(Base):
    """워크스페이스-사용자 매핑 모델"""
    
    __tablename__ = "workspace_user_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 외래키
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # 권한 정보
    permission_level = Column(
        Enum(WorkspacePermissionLevel), 
        default=WorkspacePermissionLevel.MEMBER,
        nullable=False
    )
    
    # 매핑 메타데이터
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # 권한 부여자
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # 시스템 필드
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 제약 조건: 워크스페이스당 사용자별 유일한 매핑
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user'),
    )
    
    # Relationships
    workspace = relationship("Workspace", back_populates="user_mappings")
    user = relationship("User", foreign_keys=[user_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f"<WorkspaceUserMapping workspace={self.workspace_id} user={self.user_id} permission={self.permission_level.value}>"
    
    def to_dict(self) -> dict:
        """딕셔너리 형태로 변환"""
        return {
            "id": str(self.id),
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "permission_level": self.permission_level.value,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class WorkspaceGroupMapping(Base):
    """워크스페이스-그룹 매핑 모델"""
    
    __tablename__ = "workspace_group_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 외래키
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    
    # 권한 정보
    permission_level = Column(
        Enum(WorkspacePermissionLevel), 
        default=WorkspacePermissionLevel.MEMBER,
        nullable=False
    )
    
    # 매핑 메타데이터
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # 권한 부여자
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # 시스템 필드
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 제약 조건: 워크스페이스당 그룹별 유일한 매핑
    __table_args__ = (
        UniqueConstraint('workspace_id', 'group_id', name='uq_workspace_group'),
    )
    
    # Relationships
    workspace = relationship("Workspace", back_populates="group_mappings")
    group = relationship("Group", back_populates="workspace_group_mappings")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f"<WorkspaceGroupMapping workspace={self.workspace_id} group={self.group_id} permission={self.permission_level.value}>"
    
    def to_dict(self) -> dict:
        """딕셔너리 형태로 변환"""
        return {
            "id": str(self.id),
            "workspace_id": self.workspace_id,
            "group_id": str(self.group_id),
            "permission_level": self.permission_level.value,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }