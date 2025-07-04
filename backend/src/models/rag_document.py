"""
RAG Document Model
RAG 컬렉션에 업로드된 문서 정보를 저장하는 모델
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, BigInteger, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.core.database import Base

if TYPE_CHECKING:
    from .rag_collection import RAGCollection


class RAGDocumentStatus(str, Enum):
    """RAG Document 상태"""
    PENDING = "pending"          # 업로드 완료, 처리 대기
    PROCESSING = "processing"    # 처리 중 (파싱, 임베딩)
    COMPLETED = "completed"      # 처리 완료
    ERROR = "error"              # 에러 발생
    DELETED = "deleted"          # 삭제됨


class RAGDocumentType(str, Enum):
    """지원하는 문서 타입"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    RTF = "rtf"


class RAGDocument(Base):
    """RAG Document 모델"""
    
    __tablename__ = "rag_documents"
    
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
    
    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(10),  # 단순 문자열로 변경
        nullable=False
    )
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)  # SHA256 해시
    
    # Processing Information
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status and Error Handling
    status: Mapped[str] = mapped_column(
        String(20),  # 단순 문자열로 변경
        default="pending",
        nullable=False,
        index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_metadata: Mapped[str | None] = mapped_column(Text)  # JSON 형태로 저장
    
    # User Information
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    collection: Mapped["RAGCollection"] = relationship(
        "RAGCollection",
        back_populates="documents"
    )
    
    def __repr__(self) -> str:
        return f"<RAGDocument(id={self.id}, filename={self.filename}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "collection_id": str(self.collection_id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_hash": self.file_hash,
            "chunk_count": self.chunk_count,
            "vector_count": self.vector_count,
            "status": self.status,
            "error_message": self.error_message,
            "processing_metadata": self.processing_metadata,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }
    
    @property
    def is_processing_complete(self) -> bool:
        """처리가 완료되었는지 확인"""
        return self.status == RAGDocumentStatus.COMPLETED
    
    @property
    def has_error(self) -> bool:
        """에러가 있는지 확인"""
        return self.status == RAGDocumentStatus.ERROR
    
    @property
    def file_size_mb(self) -> float:
        """파일 크기를 MB로 반환"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """지원하는 파일 확장자 목록 반환"""
        return [doc_type.value for doc_type in RAGDocumentType]
    
    @classmethod
    def get_file_type_from_filename(cls, filename: str) -> RAGDocumentType | None:
        """파일명에서 문서 타입 추출"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        try:
            return RAGDocumentType(extension)
        except ValueError:
            return None