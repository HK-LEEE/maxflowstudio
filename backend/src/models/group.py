"""
Group Model
그룹 정보를 저장하는 모델
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.core.database import Base


class Group(Base):
    """그룹 모델"""
    
    __tablename__ = "groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # 그룹 설정
    is_active = Column(Boolean, default=True)
    is_system_group = Column(Boolean, default=False)  # 시스템 그룹 여부
    
    # 시스템 필드
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), nullable=True)  # 생성자 ID
    
    # Relationships
    workspace_group_mappings = relationship(
        "WorkspaceGroupMapping", 
        back_populates="group",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Group {self.name} (id={self.id})>"
    
    def get_member_count(self) -> int:
        """그룹 멤버 수 (User 모델의 group_id 필드 기반)"""
        # Note: 실제 사용시에는 데이터베이스 세션이 필요하므로
        # admin.py에서 별도로 계산하여 설정합니다
        return getattr(self, '_member_count', 0)
    
    @property
    def workspace_count(self) -> int:
        """이 그룹이 접근할 수 있는 워크스페이스 수"""
        return len(self.workspace_group_mappings)
    
    def to_dict(self) -> dict:
        """딕셔너리 형태로 변환"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_system_group": self.is_system_group,
            "member_count": self.get_member_count(),
            "workspace_count": self.workspace_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }