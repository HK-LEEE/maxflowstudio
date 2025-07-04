"""
Flow Template Model
템플릿 관리를 위한 데이터베이스 모델
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.core.database import Base
import uuid


class FlowTemplate(Base):
    """
    Flow Template 모델
    관리자가 생성한 flow 템플릿을 저장하는 테이블
    """
    __tablename__ = "flow_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True, default="General")
    
    # Flow 정의 (nodes, edges 등)
    definition = Column(JSON, nullable=False)
    
    # 템플릿 썸네일 이미지 URL
    thumbnail = Column(Text, nullable=True)
    
    # 공개 여부
    is_public = Column(Boolean, default=True, nullable=False)
    
    # 생성자 정보
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 사용 통계
    usage_count = Column(Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f"<FlowTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    @property
    def display_name(self):
        """템플릿 표시용 이름 (카테고리 포함)"""
        if self.category and self.category != "General":
            return f"[{self.category}] {self.name}"
        return self.name
    
    def to_dict(self):
        """딕셔너리 형태로 변환"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "definition": self.definition,
            "thumbnail": self.thumbnail,
            "is_public": self.is_public,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count,
            "display_name": self.display_name
        }