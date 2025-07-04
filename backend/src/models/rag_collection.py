"""
RAG Collection Model
워크스페이스별 RAG 컬렉션 정보를 저장하는 모델
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.core.database import Base

if TYPE_CHECKING:
    from .workspace import Workspace
    from .rag_document import RAGDocument
    from .rag_search_history import RAGSearchHistory


class RAGCollectionStatus(str, Enum):
    """RAG Collection 상태"""
    ACTIVE = "active"        # 활성 상태
    LEARNING = "learning"    # 학습 중
    ERROR = "error"          # 에러 상태
    INACTIVE = "inactive"    # 비활성 상태


class RAGCollection(Base):
    """RAG Collection 모델"""
    
    __tablename__ = "rag_collections"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign Keys
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Collection Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Status and Metrics
    status: Mapped[str] = mapped_column(
        String(50),  # 단순 문자열로 변경
        default="active",
        nullable=False
    )
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Qdrant Integration
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    
    # Creator and Modifier Information
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(36))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="rag_collections"
    )
    
    documents: Mapped[List["RAGDocument"]] = relationship(
        "RAGDocument",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="RAGDocument.uploaded_at.desc()"
    )
    
    search_history: Mapped[List["RAGSearchHistory"]] = relationship(
        "RAGSearchHistory",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="RAGSearchHistory.created_at.desc()"
    )
    
    def __repr__(self) -> str:
        return f"<RAGCollection(id={self.id}, name={self.name}, workspace_id={self.workspace_id})>"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "document_count": self.document_count,
            "vector_count": self.vector_count,
            "qdrant_collection_name": self.qdrant_collection_name,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def generate_qdrant_collection_name(cls, workspace_id: str, collection_name: str) -> str:
        """Qdrant 컬렉션명 생성 (중복 방지를 위해 UUID 추가)"""
        safe_name = collection_name.replace(" ", "_").replace("-", "_").lower()
        safe_workspace = workspace_id.replace("-", "_")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"rag_{safe_workspace}_{safe_name}_{unique_suffix}"