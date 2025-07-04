"""
RAG Search History Model
RAG 검색 기록을 저장하는 모델
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.core.database import Base

if TYPE_CHECKING:
    from .rag_collection import RAGCollection


class RAGSearchHistory(Base):
    """RAG Search History 모델"""
    
    __tablename__ = "rag_search_history"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign Keys
    collection_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rag_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Search Information
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Search Metadata (JSON 형태로 저장)
    search_metadata: Mapped[dict | None] = mapped_column(JSON)
    
    # Performance Metrics
    execution_time: Mapped[float | None] = mapped_column(Float)  # 실행 시간 (초)
    retrieved_documents_count: Mapped[int | None] = mapped_column()  # 검색된 문서 수
    reranked_documents_count: Mapped[int | None] = mapped_column()   # 재순위화된 문서 수
    
    # Search Result Quality Metrics
    relevance_score: Mapped[float | None] = mapped_column(Float)  # 관련성 점수
    confidence_score: Mapped[float | None] = mapped_column(Float)  # 신뢰도 점수
    
    # User Information
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # User Feedback (선택적)
    user_rating: Mapped[int | None] = mapped_column()  # 1-5점 평가
    user_feedback: Mapped[str | None] = mapped_column(Text)  # 사용자 피드백
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    collection: Mapped["RAGCollection"] = relationship(
        "RAGCollection",
        back_populates="search_history"
    )
    
    def __repr__(self) -> str:
        return f"<RAGSearchHistory(id={self.id}, query={self.query[:50]}...)>"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "collection_id": str(self.collection_id),
            "query": self.query,
            "response": self.response,
            "search_metadata": self.search_metadata,
            "execution_time": self.execution_time,
            "retrieved_documents_count": self.retrieved_documents_count,
            "reranked_documents_count": self.reranked_documents_count,
            "relevance_score": self.relevance_score,
            "confidence_score": self.confidence_score,
            "user_id": self.user_id,
            "user_rating": self.user_rating,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def execution_time_formatted(self) -> str:
        """실행 시간을 포맷된 문자열로 반환"""
        if self.execution_time is None:
            return "N/A"
        if self.execution_time < 1:
            return f"{self.execution_time * 1000:.0f}ms"
        else:
            return f"{self.execution_time:.2f}s"
    
    @property
    def has_user_feedback(self) -> bool:
        """사용자 피드백이 있는지 확인"""
        return self.user_rating is not None or bool(self.user_feedback)
    
    def add_user_feedback(self, rating: int | None = None, feedback: str | None = None) -> None:
        """사용자 피드백 추가"""
        if rating is not None and 1 <= rating <= 5:
            self.user_rating = rating
        if feedback:
            self.user_feedback = feedback