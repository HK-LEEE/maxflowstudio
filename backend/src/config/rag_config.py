"""
RAG Configuration
RAG 시스템을 위한 설정 클래스 및 유틸리티
"""

import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field, validator

from .settings import get_settings


class RAGConfig(BaseModel):
    """RAG 시스템 설정을 위한 Pydantic 모델"""
    
    # File Storage Configuration
    upload_dir: str = Field(description="RAG 파일 업로드 디렉토리")
    max_file_size: int = Field(description="최대 파일 크기 (바이트)")
    
    # Ollama Configuration
    ollama_base_url: str = Field(description="Ollama 서버 URL")
    embedding_model: str = Field(description="임베딩 모델명")
    llm_model: str = Field(description="LLM 모델명")
    
    # Qdrant Configuration
    qdrant_url: str = Field(description="Qdrant 서버 URL")
    qdrant_api_key: str = Field(description="Qdrant API 키")
    
    # Document Processing Parameters
    chunk_size: int = Field(ge=100, le=5000, description="문서 청크 크기")
    chunk_overlap: int = Field(ge=0, le=1000, description="청크 오버랩 크기")
    
    # RAG Retrieval Parameters  
    retriever_k: int = Field(ge=1, le=50, description="초기 검색 문서 수")
    rerank_top_n: int = Field(ge=1, le=20, description="재순위화 후 선택할 문서 수")
    
    # Re-ranker Configuration
    reranker_model: str = Field(description="재순위화 모델명")
    reranker_cache_dir: str = Field(description="재순위화 모델 캐시 디렉토리")
    
    # Supported File Types
    supported_extensions: List[str] = Field(
        default=["pdf", "docx", "doc", "txt", "md", "html", "rtf"],
        description="지원하는 파일 확장자 목록"
    )
    
    @validator('max_file_size')
    def validate_max_file_size(cls, v):
        """최대 파일 크기 유효성 검사"""
        if v < 1024 * 1024:  # 1MB 미만
            raise ValueError("최대 파일 크기는 1MB 이상이어야 합니다")
        if v > 500 * 1024 * 1024:  # 500MB 초과
            raise ValueError("최대 파일 크기는 500MB 이하여야 합니다")
        return v
    
    @validator('rerank_top_n')
    def validate_rerank_top_n(cls, v, values):
        """재순위화 문서 수가 초기 검색 문서 수보다 작은지 확인"""
        if 'retriever_k' in values and v > values['retriever_k']:
            raise ValueError("재순위화 문서 수는 초기 검색 문서 수보다 작거나 같아야 합니다")
        return v
    
    @validator('upload_dir')
    def validate_upload_dir(cls, v):
        """업로드 디렉토리 존재 여부 확인 및 생성"""
        if not os.path.exists(v):
            try:
                os.makedirs(v, exist_ok=True)
            except Exception as e:
                raise ValueError(f"업로드 디렉토리 생성 실패: {e}")
        return v
    
    def get_workspace_upload_dir(self, workspace_id: str) -> str:
        """워크스페이스별 업로드 디렉토리 경로 반환"""
        workspace_dir = os.path.join(self.upload_dir, workspace_id)
        os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir
    
    def get_collection_upload_dir(self, workspace_id: str, collection_name: str) -> str:
        """컬렉션별 업로드 디렉토리 경로 반환"""
        # 안전한 파일명으로 변환
        safe_collection_name = "".join(c for c in collection_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_collection_name = safe_collection_name.replace(' ', '_')
        
        collection_dir = os.path.join(self.get_workspace_upload_dir(workspace_id), safe_collection_name)
        
        # documents와 metadata 하위 디렉토리 생성
        documents_dir = os.path.join(collection_dir, "documents")
        metadata_dir = os.path.join(collection_dir, "metadata")
        
        os.makedirs(documents_dir, exist_ok=True)
        os.makedirs(metadata_dir, exist_ok=True)
        
        return collection_dir
    
    def is_supported_file(self, filename: str) -> bool:
        """지원하는 파일 타입인지 확인"""
        if '.' not in filename:
            return False
        extension = filename.lower().split('.')[-1]
        return extension in self.supported_extensions
    
    def get_file_size_mb(self, file_size_bytes: int) -> float:
        """바이트를 MB로 변환"""
        return round(file_size_bytes / (1024 * 1024), 2)
    
    def is_file_size_valid(self, file_size_bytes: int) -> bool:
        """파일 크기가 유효한지 확인"""
        return file_size_bytes <= self.max_file_size
    
    class Config:
        """Pydantic 설정"""
        use_enum_values = True
        validate_assignment = True


@lru_cache()
def get_rag_config() -> RAGConfig:
    """RAG 설정 인스턴스를 반환 (캐시됨)"""
    settings = get_settings()
    
    return RAGConfig(
        upload_dir=settings.RAG_UPLOAD_DIR,
        max_file_size=settings.RAG_MAX_FILE_SIZE,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        embedding_model=settings.RAG_EMBEDDING_MODEL,
        llm_model=settings.RAG_LLM_MODEL,
        qdrant_url=settings.QDRANT_URL,
        qdrant_api_key=settings.QDRANT_API_KEY,
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        retriever_k=settings.RAG_RETRIEVER_K,
        rerank_top_n=settings.RAG_RERANK_TOP_N,
        reranker_model=settings.RAG_RERANKER_MODEL,
        reranker_cache_dir=settings.RAG_RERANKER_CACHE_DIR
    )