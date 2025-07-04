"""
RAG Schemas
RAG API를 위한 Pydantic 스키마 정의
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import numpy as np

from pydantic import BaseModel, Field, validator

from src.models.rag_collection import RAGCollectionStatus
from src.models.rag_document import RAGDocumentStatus, RAGDocumentType


# ============ NumPy Type Conversion Utilities ============

def convert_numpy_types(obj):
    """모든 NumPy 타입을 Python 기본 타입으로 변환"""
    try:
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif hasattr(obj, 'item'):  # NumPy 타입인 경우
            return obj.item()
        elif isinstance(obj, (np.integer, np.floating, np.complexfloating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # NumPy 스칼라 타입들을 명시적으로 처리
        elif str(type(obj)).startswith("<class 'numpy."):
            return obj.item() if hasattr(obj, 'item') else float(obj)
        else:
            return obj
    except Exception:
        # 변환 실패 시 원본 반환 (마지막 안전장치)
        return obj


# ============ RAG Collection Schemas ============

class RAGCollectionBase(BaseModel):
    """RAG Collection 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="컬렉션 이름")
    description: Optional[str] = Field(None, description="컬렉션 설명")


class RAGCollectionCreate(RAGCollectionBase):
    """RAG Collection 생성 스키마"""
    pass


class RAGCollectionUpdate(BaseModel):
    """RAG Collection 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="컬렉션 이름")
    description: Optional[str] = Field(None, description="컬렉션 설명")
    is_active: Optional[bool] = Field(None, description="활성화 상태")


class RAGCollectionResponse(RAGCollectionBase):
    """RAG Collection 응답 스키마"""
    id: UUID = Field(..., description="컬렉션 ID")
    workspace_id: str = Field(..., description="워크스페이스 ID")
    status: RAGCollectionStatus = Field(..., description="컬렉션 상태")
    document_count: int = Field(..., description="문서 수")
    vector_count: int = Field(..., description="벡터 수")
    qdrant_collection_name: str = Field(..., description="Qdrant 컬렉션명")
    created_by: str = Field(..., description="생성자 ID")
    updated_by: Optional[str] = Field(None, description="수정자 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    is_active: bool = Field(..., description="활성화 상태")

    class Config:
        from_attributes = True


class RAGCollectionListResponse(BaseModel):
    """RAG Collection 목록 응답 스키마"""
    collections: List[RAGCollectionResponse] = Field(..., description="컬렉션 목록")
    total: int = Field(..., description="전체 컬렉션 수")


# ============ RAG Document Schemas ============

class RAGDocumentResponse(BaseModel):
    """RAG Document 응답 스키마"""
    id: UUID = Field(..., description="문서 ID")
    collection_id: UUID = Field(..., description="컬렉션 ID")
    filename: str = Field(..., description="파일명")
    original_filename: str = Field(..., description="원본 파일명")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    file_type: RAGDocumentType = Field(..., description="파일 타입")
    mime_type: Optional[str] = Field(None, description="MIME 타입")
    chunk_count: int = Field(..., description="청크 수")
    vector_count: int = Field(..., description="벡터 수")
    status: RAGDocumentStatus = Field(..., description="문서 상태")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    uploaded_by: str = Field(..., description="업로드한 사용자 ID")
    uploaded_at: datetime = Field(..., description="업로드 일시")
    processed_at: Optional[datetime] = Field(None, description="처리 완료 일시")
    
    @property
    def file_size_mb(self) -> float:
        """파일 크기를 MB로 반환"""
        return round(self.file_size / (1024 * 1024), 2)

    class Config:
        from_attributes = True


class RAGDocumentListResponse(BaseModel):
    """RAG Document 목록 응답 스키마"""
    documents: List[RAGDocumentResponse] = Field(..., description="문서 목록")
    total: int = Field(..., description="전체 문서 수")


class RAGDocumentUploadResponse(BaseModel):
    """RAG Document 업로드 응답 스키마"""
    document_id: UUID = Field(..., description="업로드된 문서 ID")
    filename: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기")
    status: RAGDocumentStatus = Field(..., description="문서 상태")
    message: str = Field(..., description="응답 메시지")


# ============ RAG Search Schemas ============

class RAGSearchRequest(BaseModel):
    """RAG 검색 요청 스키마"""
    query: str = Field(..., min_length=1, max_length=1000, description="검색 쿼리")
    include_metadata: bool = Field(default=True, description="메타데이터 포함 여부")
    
    @validator('query')
    def validate_query(cls, v):
        """쿼리 유효성 검사"""
        if not v.strip():
            raise ValueError("검색 쿼리는 비어있을 수 없습니다")
        return v.strip()


class RAGSearchDocument(BaseModel):
    """검색된 문서 정보"""
    document_id: UUID = Field(..., description="문서 ID")
    filename: str = Field(..., description="파일명")
    content: str = Field(..., description="문서 내용")
    score: float = Field(..., description="관련성 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="문서 메타데이터")
    
    @validator('score', pre=True)
    def convert_numpy_score(cls, v):
        """NumPy 타입을 Python 기본 타입으로 변환"""
        if hasattr(v, 'item'):  # NumPy 타입인 경우
            return float(v.item())
        return float(v)
    
    @validator('metadata', pre=True)
    def convert_numpy_metadata(cls, v):
        """메타데이터의 모든 NumPy 타입을 Python 기본 타입으로 변환"""
        return convert_numpy_types(v)


class RAGSearchStep(BaseModel):
    """RAG 검색 단계 정보"""
    step_name: str = Field(..., description="단계명")
    description: str = Field(..., description="단계 설명")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="입력 데이터")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="출력 데이터")
    execution_time: float = Field(..., description="실행 시간 (초)")
    status: str = Field(..., description="단계 상태")
    
    @validator('execution_time', pre=True)
    def convert_numpy_execution_time(cls, v):
        """NumPy 타입을 Python 기본 타입으로 변환"""
        if hasattr(v, 'item'):  # NumPy 타입인 경우
            return float(v.item())
        return float(v)
    
    @validator('input_data', 'output_data', pre=True)
    def convert_numpy_data(cls, v):
        """입력/출력 데이터의 모든 NumPy 타입을 Python 기본 타입으로 변환"""
        return convert_numpy_types(v)


class RAGSearchResult(BaseModel):
    """RAG 검색 결과 스키마"""
    query: str = Field(..., description="검색 쿼리")
    response: str = Field(..., description="생성된 응답")
    retrieved_documents: List[RAGSearchDocument] = Field(..., description="검색된 문서 목록")
    search_steps: List[RAGSearchStep] = Field(..., description="검색 단계별 정보")
    total_execution_time: float = Field(..., description="전체 실행 시간 (초)")
    relevance_score: Optional[float] = Field(None, description="관련성 점수")
    confidence_score: Optional[float] = Field(None, description="신뢰도 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="검색 메타데이터")
    
    @validator('total_execution_time', 'relevance_score', 'confidence_score', pre=True)
    def convert_numpy_floats(cls, v):
        """NumPy 타입을 Python 기본 타입으로 변환"""
        if v is None:
            return v
        if hasattr(v, 'item'):  # NumPy 타입인 경우
            return float(v.item())
        return float(v)
    
    @validator('metadata', pre=True)
    def convert_numpy_metadata(cls, v):
        """메타데이터의 모든 NumPy 타입을 Python 기본 타입으로 변환"""
        return convert_numpy_types(v)


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답 스키마"""
    search_id: UUID = Field(..., description="검색 ID")
    result: RAGSearchResult = Field(..., description="검색 결과")
    created_at: datetime = Field(..., description="검색 일시")

    class Config:
        from_attributes = True


# ============ RAG Search History Schemas ============

class RAGSearchHistoryResponse(BaseModel):
    """RAG 검색 기록 응답 스키마"""
    id: UUID = Field(..., description="검색 기록 ID")
    collection_id: UUID = Field(..., description="컬렉션 ID")
    query: str = Field(..., description="검색 쿼리")
    response: str = Field(..., description="생성된 응답")
    execution_time: Optional[float] = Field(None, description="실행 시간 (초)")
    retrieved_documents_count: Optional[int] = Field(None, description="검색된 문서 수")
    reranked_documents_count: Optional[int] = Field(None, description="재순위화된 문서 수")
    relevance_score: Optional[float] = Field(None, description="관련성 점수")
    confidence_score: Optional[float] = Field(None, description="신뢰도 점수")
    user_id: str = Field(..., description="검색한 사용자 ID")
    user_rating: Optional[int] = Field(None, description="사용자 평가 (1-5)")
    user_feedback: Optional[str] = Field(None, description="사용자 피드백")
    created_at: datetime = Field(..., description="검색 일시")

    class Config:
        from_attributes = True


class RAGSearchHistoryListResponse(BaseModel):
    """RAG 검색 기록 목록 응답 스키마"""
    history: List[RAGSearchHistoryResponse] = Field(..., description="검색 기록 목록")
    total: int = Field(..., description="전체 검색 기록 수")


class RAGUserFeedbackRequest(BaseModel):
    """사용자 피드백 요청 스키마"""
    rating: Optional[int] = Field(None, ge=1, le=5, description="평가 점수 (1-5)")
    feedback: Optional[str] = Field(None, max_length=1000, description="피드백 내용")
    
    @validator('rating')
    def validate_rating(cls, v):
        """평가 점수 유효성 검사"""
        if v is not None and not (1 <= v <= 5):
            raise ValueError("평가 점수는 1-5 사이여야 합니다")
        return v


# ============ Statistics Schemas ============

class RAGCollectionStats(BaseModel):
    """RAG 컬렉션 통계 스키마"""
    total_collections: int = Field(..., description="전체 컬렉션 수")
    active_collections: int = Field(..., description="활성 컬렉션 수")
    total_documents: int = Field(..., description="전체 문서 수")
    total_vectors: int = Field(..., description="전체 벡터 수")
    average_documents_per_collection: float = Field(..., description="컬렉션당 평균 문서 수")
    total_file_size_mb: float = Field(..., description="전체 파일 크기 (MB)")


class RAGWorkspaceStats(BaseModel):
    """워크스페이스 RAG 통계 스키마"""
    workspace_id: str = Field(..., description="워크스페이스 ID")
    collection_stats: RAGCollectionStats = Field(..., description="컬렉션 통계")
    recent_searches: int = Field(..., description="최근 검색 수 (7일)")
    popular_queries: List[str] = Field(..., description="인기 검색어")


# ============ Error Schemas ============

class RAGErrorResponse(BaseModel):
    """RAG 에러 응답 스키마"""
    error_code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(None, description="에러 상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")