"""
RAG Service
RAG 기능을 위한 비즈니스 로직 서비스
"""

import os
import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from src.models.rag_collection import RAGCollection, RAGCollectionStatus
from src.models.rag_document import RAGDocument, RAGDocumentStatus, RAGDocumentType
from src.models.rag_search_history import RAGSearchHistory
from src.schemas.rag import (
    RAGSearchResult,
    RAGCollectionStats,
    RAGWorkspaceStats
)
from src.config.rag_config import get_rag_config
from src.services.rag_agent import ProductionRAGAgent
import structlog

logger = structlog.get_logger()


class RAGService:
    """RAG 서비스 클래스"""
    
    def __init__(self):
        self.config = get_rag_config()
        self._agent_cache = {}  # 컬렉션별 에이전트 캐시
    
    def _get_agent(self, collection_name: str) -> ProductionRAGAgent:
        """컬렉션별 RAG Agent 반환 (캐시 사용)"""
        if collection_name not in self._agent_cache:
            self._agent_cache[collection_name] = ProductionRAGAgent(self.config)
        return self._agent_cache[collection_name]
    
    async def create_collection_in_qdrant(self, collection: RAGCollection) -> bool:
        """Qdrant에 컬렉션 생성"""
        try:
            agent = self._get_agent(collection.qdrant_collection_name)
            success = await agent.create_collection(collection.qdrant_collection_name)
            
            if success:
                logger.info(f"Qdrant 컬렉션 생성 성공: {collection.qdrant_collection_name}")
            else:
                logger.error(f"Qdrant 컬렉션 생성 실패: {collection.qdrant_collection_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Qdrant 컬렉션 생성 중 오류: {e}")
            return False
    
    async def upload_and_process_document(
        self,
        collection: RAGCollection,
        file_path: str,
        original_filename: str,
        uploaded_by: str,
        db: AsyncSession
    ) -> RAGDocument:
        """문서 업로드 및 처리"""
        
        try:
            # 파일 정보 수집
            file_size = os.path.getsize(file_path)
            file_type = RAGDocument.get_file_type_from_filename(original_filename)
            
            if not file_type:
                raise ValueError(f"지원하지 않는 파일 형식: {original_filename}")
            
            # 파일 해시 계산
            file_hash = self._calculate_file_hash(file_path)
            
            # 중복 파일 확인 (성공한 문서만 중복으로 간주)
            existing_doc = await self._check_duplicate_document(
                collection.id, file_hash, db
            )
            if existing_doc:
                # 기존 문서가 에러 상태라면 삭제하고 재업로드 허용
                if existing_doc.status == "error":
                    logger.info(f"에러 상태 문서 재업로드 허용: {existing_doc.id}")
                    await db.delete(existing_doc)
                    await db.commit()
                elif existing_doc.status == "completed":
                    raise ValueError("동일한 파일이 이미 성공적으로 업로드되어 있습니다")
                elif existing_doc.status == "processing":
                    raise ValueError("동일한 파일이 현재 처리 중입니다")
            
            # 문서 레코드 생성
            document = RAGDocument(
                collection_id=collection.id,
                filename=f"{uuid.uuid4()}_{original_filename}",
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                file_hash=file_hash,
                uploaded_by=uploaded_by
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            # 비동기적으로 문서 처리 시작
            await self._process_document_async(document, collection, db)
            
            logger.info(f"문서 업로드 완료: {document.id}")
            return document
            
        except Exception as e:
            await db.rollback()
            logger.error(f"문서 업로드 실패: {e}")
            raise
    
    async def _process_document_async(
        self,
        document: RAGDocument,
        collection: RAGCollection,
        db: AsyncSession
    ):
        """문서 비동기 처리"""
        
        try:
            # 상태를 처리 중으로 변경
            document.status = "processing"
            await db.commit()
            
            # 문서 메타데이터 준비
            document_metadata = {
                "document_id": str(document.id),
                "collection_id": str(collection.id),
                "original_filename": document.original_filename,
                "uploaded_by": document.uploaded_by,
                "uploaded_at": document.uploaded_at.isoformat()
            }
            
            # RAG Agent로 문서 처리
            agent = self._get_agent(collection.qdrant_collection_name)
            result = await agent.upload_and_process_document(
                collection.qdrant_collection_name,
                document.file_path,
                document_metadata
            )
            
            if result["success"]:
                # 처리 성공
                document.status = "completed"
                document.chunk_count = result["chunks_created"]
                document.vector_count = result["vectors_stored"]
                document.processed_at = datetime.utcnow()
                document.processing_metadata = json.dumps({
                    "processing_time": result["processing_time"],
                    "chunks_created": result["chunks_created"],
                    "vectors_stored": result["vectors_stored"]
                })
                
                # 컬렉션 통계 업데이트
                collection.document_count += 1
                collection.vector_count += result["vectors_stored"]
                
            else:
                # 처리 실패
                document.status = "error"
                document.error_message = result["error"]
                document.processing_metadata = json.dumps(result)
            
            await db.commit()
            
            logger.info(f"문서 처리 완료: {document.id} (상태: {document.status})")
            
        except Exception as e:
            # 에러 상태로 업데이트
            document.status = "error"
            document.error_message = str(e)
            await db.commit()
            
            logger.error(f"문서 처리 실패: {document.id} - {e}")
    
    async def search_collection(
        self,
        collection: RAGCollection,
        query: str,
        user_id: str,
        include_metadata: bool = True,
        db: AsyncSession = None
    ) -> RAGSearchResult:
        """컬렉션에서 검색 수행"""
        
        try:
            # RAG Agent로 검색 실행
            agent = self._get_agent(collection.qdrant_collection_name)
            result = await agent.search(
                collection.qdrant_collection_name,
                query,
                include_metadata
            )
            
            # 검색 기록 저장 (선택적)
            if db:
                await self._save_search_history(
                    collection.id,
                    query,
                    result.response,
                    result.total_execution_time,
                    len(result.retrieved_documents),
                    user_id,
                    result.metadata,
                    db
                )
            
            logger.info(f"검색 완료: {query[:50]}... (컬렉션: {collection.name})")
            return result
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            raise
    
    async def _save_search_history(
        self,
        collection_id: uuid.UUID,
        query: str,
        response: str,
        execution_time: float,
        retrieved_count: int,
        user_id: str,
        metadata: Dict[str, Any],
        db: AsyncSession
    ):
        """검색 기록 저장"""
        
        try:
            search_history = RAGSearchHistory(
                collection_id=collection_id,
                query=query,
                response=response,
                execution_time=execution_time,
                retrieved_documents_count=retrieved_count,
                user_id=user_id,
                search_metadata=metadata
            )
            
            db.add(search_history)
            await db.commit()
            
        except Exception as e:
            logger.warning(f"검색 기록 저장 실패: {e}")
    
    async def get_collection_documents(
        self,
        collection_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status: Optional[RAGDocumentStatus] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """컬렉션의 문서 목록 조회"""
        
        try:
            query = select(RAGDocument).where(RAGDocument.collection_id == collection_id)
            
            if status:
                query = query.where(RAGDocument.status == status)
            
            # 전체 개수 조회
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # 페이지네이션
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit).order_by(RAGDocument.uploaded_at.desc())
            
            result = await db.execute(query)
            documents = result.scalars().all()
            
            return {
                "documents": documents,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"문서 목록 조회 실패: {e}")
            raise
    
    async def get_search_history(
        self,
        collection_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """검색 기록 조회"""
        
        try:
            query = select(RAGSearchHistory).where(RAGSearchHistory.collection_id == collection_id)
            
            if user_id:
                query = query.where(RAGSearchHistory.user_id == user_id)
            
            # 전체 개수 조회
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # 페이지네이션
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit).order_by(RAGSearchHistory.created_at.desc())
            
            result = await db.execute(query)
            history = result.scalars().all()
            
            return {
                "history": history,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"검색 기록 조회 실패: {e}")
            raise
    
    async def get_collection_stats(
        self,
        collection_id: uuid.UUID,
        db: AsyncSession
    ) -> RAGCollectionStats:
        """컬렉션 통계 조회"""
        
        try:
            # 컬렉션 정보 조회
            collection_query = select(RAGCollection).where(RAGCollection.id == collection_id)
            collection_result = await db.execute(collection_query)
            collection = collection_result.scalar_one_or_none()
            
            if not collection:
                raise ValueError("컬렉션을 찾을 수 없습니다")
            
            # 문서 통계
            doc_count_query = select(func.count(RAGDocument.id)).where(
                RAGDocument.collection_id == collection_id
            )
            doc_count_result = await db.execute(doc_count_query)
            total_documents = doc_count_result.scalar() or 0
            
            # 파일 크기 통계
            file_size_query = select(func.sum(RAGDocument.file_size)).where(
                and_(
                    RAGDocument.collection_id == collection_id,
                    RAGDocument.status == "completed"
                )
            )
            file_size_result = await db.execute(file_size_query)
            total_file_size = file_size_result.scalar() or 0
            
            stats = RAGCollectionStats(
                total_collections=1,
                active_collections=1 if collection.is_active else 0,
                total_documents=total_documents,
                total_vectors=collection.vector_count,
                average_documents_per_collection=float(total_documents),
                total_file_size_mb=round(total_file_size / (1024 * 1024), 2)
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"컬렉션 통계 조회 실패: {e}")
            raise
    
    async def get_workspace_stats(
        self,
        workspace_id: str,
        db: AsyncSession
    ) -> RAGWorkspaceStats:
        """워크스페이스 RAG 통계 조회"""
        
        try:
            # 워크스페이스의 모든 컬렉션 조회
            collections_query = select(RAGCollection).where(
                RAGCollection.workspace_id == workspace_id
            )
            collections_result = await db.execute(collections_query)
            collections = collections_result.scalars().all()
            
            total_collections = len(collections)
            active_collections = len([c for c in collections if c.is_active])
            total_documents = sum(c.document_count for c in collections)
            total_vectors = sum(c.vector_count for c in collections)
            
            # 파일 크기 계산
            if collections:
                collection_ids = [c.id for c in collections]
                file_size_query = select(func.sum(RAGDocument.file_size)).where(
                    and_(
                        RAGDocument.collection_id.in_(collection_ids),
                        RAGDocument.status == "completed"
                    )
                )
                file_size_result = await db.execute(file_size_query)
                total_file_size = file_size_result.scalar() or 0
            else:
                total_file_size = 0
            
            collection_stats = RAGCollectionStats(
                total_collections=total_collections,
                active_collections=active_collections,
                total_documents=total_documents,
                total_vectors=total_vectors,
                average_documents_per_collection=float(total_documents / max(total_collections, 1)),
                total_file_size_mb=round(total_file_size / (1024 * 1024), 2)
            )
            
            # 최근 검색 통계 (7일)
            from datetime import timedelta
            recent_date = datetime.utcnow() - timedelta(days=7)
            
            if collections:
                recent_searches_query = select(func.count(RAGSearchHistory.id)).where(
                    and_(
                        RAGSearchHistory.collection_id.in_(collection_ids),
                        RAGSearchHistory.created_at >= recent_date
                    )
                )
                recent_searches_result = await db.execute(recent_searches_query)
                recent_searches = recent_searches_result.scalar() or 0
            else:
                recent_searches = 0
            
            workspace_stats = RAGWorkspaceStats(
                workspace_id=workspace_id,
                collection_stats=collection_stats,
                recent_searches=recent_searches,
                popular_queries=[]  # TODO: 인기 검색어 구현
            )
            
            return workspace_stats
            
        except Exception as e:
            logger.error(f"워크스페이스 통계 조회 실패: {e}")
            raise
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """파일 SHA256 해시 계산"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"파일 해시 계산 실패: {e}")
            return ""
    
    async def _check_duplicate_document(
        self,
        collection_id: uuid.UUID,
        file_hash: str,
        db: AsyncSession
    ) -> Optional[RAGDocument]:
        """중복 문서 확인"""
        try:
            if not file_hash:
                return None
                
            query = select(RAGDocument).where(
                and_(
                    RAGDocument.collection_id == collection_id,
                    RAGDocument.file_hash == file_hash,
                    RAGDocument.status != "deleted"
                )
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"중복 문서 확인 실패: {e}")
            return None
    
    async def delete_document(
        self,
        document: RAGDocument,
        collection: RAGCollection,
        db: AsyncSession
    ) -> bool:
        """문서 삭제 (파일, 데이터베이스 레코드, 벡터 데이터)"""
        
        try:
            # 1. 벡터 데이터 삭제 (Qdrant에서)
            try:
                agent = self._get_agent(collection.qdrant_collection_name)
                vector_deleted = await agent.delete_document_vectors(
                    collection.qdrant_collection_name,
                    str(document.id)
                )
                if vector_deleted:
                    logger.info(f"벡터 데이터 삭제 완료: 문서 {document.id}")
                else:
                    logger.warning(f"벡터 데이터 삭제 실패: 문서 {document.id}")
            except Exception as e:
                logger.error(f"벡터 데이터 삭제 실패: {e}")
                # 벡터 삭제 실패해도 계속 진행
            
            # 2. 물리적 파일 삭제
            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.unlink(document.file_path)
                    logger.info(f"파일 삭제 완료: {document.file_path}")
                except Exception as e:
                    logger.error(f"파일 삭제 실패: {e}")
                    # 파일 삭제 실패해도 계속 진행
            
            # 3. 데이터베이스 레코드 삭제
            await db.delete(document)
            
            # 4. 컬렉션 통계 업데이트
            if document.status == "completed":
                collection.document_count = max(0, collection.document_count - 1)
                collection.vector_count = max(0, collection.vector_count - document.vector_count)
            
            await db.commit()
            
            logger.info(f"문서 삭제 완료: {document.id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"문서 삭제 실패: {e}")
            return False
    
    def validate_file(self, filename: str, file_size: int) -> Dict[str, Any]:
        """파일 유효성 검사"""
        errors = []
        
        # 파일 확장자 확인
        if not self.config.is_supported_file(filename):
            errors.append(f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(self.config.supported_extensions)}")
        
        # 파일 크기 확인
        if not self.config.is_file_size_valid(file_size):
            max_size_mb = self.config.get_file_size_mb(self.config.max_file_size)
            current_size_mb = self.config.get_file_size_mb(file_size)
            errors.append(f"파일 크기가 너무 큽니다. 현재: {current_size_mb}MB, 최대: {max_size_mb}MB")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


# 전역 서비스 인스턴스
rag_service = RAGService()