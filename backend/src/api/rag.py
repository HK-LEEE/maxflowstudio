"""
RAG API Endpoints
RAG 컬렉션, 문서, 검색 관련 API
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.user import User
from src.models.workspace import Workspace
from src.models.workspace_mapping import WorkspaceUserMapping, WorkspaceGroupMapping, WorkspacePermissionLevel
from src.models.rag_collection import RAGCollection, RAGCollectionStatus
from src.models.rag_document import RAGDocument, RAGDocumentStatus
from src.models.rag_search_history import RAGSearchHistory
from src.schemas.rag import (
    RAGCollectionCreate,
    RAGCollectionUpdate,
    RAGCollectionResponse,
    RAGCollectionListResponse,
    RAGDocumentResponse,
    RAGDocumentListResponse,
    RAGDocumentUploadResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchHistoryListResponse,
    RAGUserFeedbackRequest,
    RAGCollectionStats,
    RAGWorkspaceStats
)
from src.config.rag_config import get_rag_config
import structlog

router = APIRouter()
logger = structlog.get_logger()


async def check_workspace_permission(
    workspace_id: str,
    user: User,
    required_permission: WorkspacePermissionLevel,
    db: AsyncSession
) -> bool:
    """워크스페이스 권한 확인"""
    try:
        # 워크스페이스 존재 확인
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        if not workspace or not workspace.is_active:
            return False
        
        # 슈퍼유저는 모든 권한 허용
        if user.is_superuser:
            return True
        
        # 워크스페이스 생성자는 모든 권한 허용
        if workspace.creator_user_id == user.id:
            return True
        
        # 사용자 직접 권한 확인
        user_mapping_query = select(WorkspaceUserMapping).where(
            and_(
                WorkspaceUserMapping.workspace_id == workspace_id,
                WorkspaceUserMapping.user_id == user.id
            )
        )
        user_mapping_result = await db.execute(user_mapping_query)
        user_mapping = user_mapping_result.scalar_one_or_none()
        
        if user_mapping:
            return user_mapping.permission_level.value >= required_permission.value
        
        # 그룹 권한 확인 (사용자가 그룹에 속한 경우)
        if user.group_id:
            group_mapping_query = select(WorkspaceGroupMapping).where(
                and_(
                    WorkspaceGroupMapping.workspace_id == workspace_id,
                    WorkspaceGroupMapping.group_id == uuid.UUID(user.group_id)
                )
            )
            group_mapping_result = await db.execute(group_mapping_query)
            group_mapping = group_mapping_result.scalar_one_or_none()
            
            if group_mapping:
                return group_mapping.permission_level.value >= required_permission.value
        
        return False
        
    except Exception as e:
        logger.error(f"워크스페이스 권한 확인 중 오류: {str(e)}")
        return False


async def get_accessible_workspaces(user: User, db: AsyncSession) -> List[str]:
    """사용자가 접근 가능한 워크스페이스 ID 목록 반환"""
    try:
        workspace_ids = set()
        
        # 슈퍼유저는 모든 워크스페이스 접근 가능
        if user.is_superuser:
            all_workspaces_query = select(Workspace.id).where(Workspace.is_active == True)
            result = await db.execute(all_workspaces_query)
            return [row[0] for row in result.fetchall()]
        
        # 사용자가 생성한 워크스페이스
        creator_query = select(Workspace.id).where(
            and_(Workspace.creator_user_id == user.id, Workspace.is_active == True)
        )
        creator_result = await db.execute(creator_query)
        workspace_ids.update([row[0] for row in creator_result.fetchall()])
        
        # 사용자 직접 권한이 있는 워크스페이스
        user_mapping_query = select(WorkspaceUserMapping.workspace_id).where(
            WorkspaceUserMapping.user_id == user.id
        )
        user_mapping_result = await db.execute(user_mapping_query)
        workspace_ids.update([row[0] for row in user_mapping_result.fetchall()])
        
        # 그룹 권한이 있는 워크스페이스
        if user.group_id:
            group_mapping_query = select(WorkspaceGroupMapping.workspace_id).where(
                WorkspaceGroupMapping.group_id == uuid.UUID(user.group_id)
            )
            group_mapping_result = await db.execute(group_mapping_query)
            workspace_ids.update([row[0] for row in group_mapping_result.fetchall()])
        
        return list(workspace_ids)
        
    except Exception as e:
        logger.error(f"접근 가능한 워크스페이스 조회 중 오류: {str(e)}")
        return []


# ============ RAG Collection APIs ============

@router.get("/workspaces/{workspace_id}/collections", response_model=RAGCollectionListResponse)
async def get_collections(
    workspace_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[RAGCollectionStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """워크스페이스의 RAG 컬렉션 목록 조회"""
    
    # 권한 확인
    has_permission = await check_workspace_permission(
        workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="워크스페이스 접근 권한이 없습니다")
    
    try:
        # 기본 쿼리
        query = select(RAGCollection).where(RAGCollection.workspace_id == workspace_id)
        
        # 필터 조건 추가
        if search:
            search_pattern = f"%{search}%"
            query = query.where(RAGCollection.name.ilike(search_pattern))
        
        if status:
            query = query.where(RAGCollection.status == status)
        
        # 전체 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 페이지네이션 적용
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(RAGCollection.created_at.desc())
        
        result = await db.execute(query)
        collections = result.scalars().all()
        
        logger.info(f"워크스페이스 {workspace_id}의 컬렉션 {len(collections)}개 조회")
        
        return RAGCollectionListResponse(
            collections=[RAGCollectionResponse.model_validate(col) for col in collections],
            total=total
        )
        
    except Exception as e:
        logger.error(f"컬렉션 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="컬렉션 목록 조회에 실패했습니다")


@router.post("/workspaces/{workspace_id}/collections", response_model=RAGCollectionResponse)
async def create_collection(
    workspace_id: str,
    collection_data: RAGCollectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """새 RAG 컬렉션 생성"""
    
    # 권한 확인 (MEMBER 이상 필요)
    has_permission = await check_workspace_permission(
        workspace_id, current_user, WorkspacePermissionLevel.MEMBER, db
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="컬렉션 생성 권한이 없습니다")
    
    try:
        # 동일한 이름의 컬렉션 존재 확인
        existing_query = select(RAGCollection).where(
            and_(
                RAGCollection.workspace_id == workspace_id,
                RAGCollection.name == collection_data.name
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="동일한 이름의 컬렉션이 이미 존재합니다")
        
        # Qdrant 컬렉션명 생성
        qdrant_collection_name = RAGCollection.generate_qdrant_collection_name(
            workspace_id, collection_data.name
        )
        
        # 새 컬렉션 생성
        new_collection = RAGCollection(
            workspace_id=workspace_id,
            name=collection_data.name,
            description=collection_data.description,
            status="active",  # 명시적으로 문자열 값 사용
            qdrant_collection_name=qdrant_collection_name,
            created_by=current_user.id
        )
        
        # 디버깅: 실제 값 확인
        logger.info(f"컬렉션 생성 전 status 값: {new_collection.status} (타입: {type(new_collection.status)})")
        
        db.add(new_collection)
        await db.commit()
        await db.refresh(new_collection)
        
        logger.info(f"새 컬렉션 생성: {new_collection.id} (사용자: {current_user.id})")
        
        return RAGCollectionResponse.model_validate(new_collection)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"컬렉션 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="컬렉션 생성에 실패했습니다")


@router.get("/collections/{collection_id}", response_model=RAGCollectionResponse)
async def get_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG 컬렉션 상세 조회"""
    
    try:
        # 컬렉션 조회
        query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        result = await db.execute(query)
        collection = result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="컬렉션 접근 권한이 없습니다")
        
        return RAGCollectionResponse.model_validate(collection)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"컬렉션 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="컬렉션 조회에 실패했습니다")


@router.put("/collections/{collection_id}", response_model=RAGCollectionResponse)
async def update_collection(
    collection_id: str,
    collection_data: RAGCollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG 컬렉션 수정"""
    
    try:
        # 컬렉션 조회
        query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        result = await db.execute(query)
        collection = result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (MEMBER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.MEMBER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="컬렉션 수정 권한이 없습니다")
        
        # 이름 중복 확인 (이름이 변경되는 경우)
        if collection_data.name and collection_data.name != collection.name:
            existing_query = select(RAGCollection).where(
                and_(
                    RAGCollection.workspace_id == collection.workspace_id,
                    RAGCollection.name == collection_data.name,
                    RAGCollection.id != collection.id
                )
            )
            existing_result = await db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="동일한 이름의 컬렉션이 이미 존재합니다")
        
        # 필드 업데이트
        if collection_data.name:
            collection.name = collection_data.name
        if collection_data.description is not None:
            collection.description = collection_data.description
        if collection_data.is_active is not None:
            collection.is_active = collection_data.is_active
        
        collection.updated_by = current_user.id
        
        await db.commit()
        await db.refresh(collection)
        
        logger.info(f"컬렉션 수정: {collection_id} (사용자: {current_user.id})")
        
        return RAGCollectionResponse.model_validate(collection)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"컬렉션 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="컬렉션 수정에 실패했습니다")


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG 컬렉션 삭제"""
    
    try:
        # 컬렉션 조회
        query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        result = await db.execute(query)
        collection = result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (ADMIN 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.ADMIN, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="컬렉션 삭제 권한이 없습니다")
        
        # 컬렉션 삭제 (CASCADE로 관련 문서들도 자동 삭제)
        await db.delete(collection)
        await db.commit()
        
        logger.info(f"컬렉션 삭제: {collection_id} (사용자: {current_user.id})")
        
        return {"message": "컬렉션이 성공적으로 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"컬렉션 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="컬렉션 삭제에 실패했습니다")


# ============ RAG Document APIs (스켈레톤) ============

@router.get("/collections/{collection_id}/documents", response_model=RAGDocumentListResponse)
async def get_documents(
    collection_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[RAGDocumentStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """컬렉션의 문서 목록 조회"""
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (VIEWER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="문서 목록 조회 권한이 없습니다")
        
        # RAG Service로 문서 목록 조회
        from src.services.rag_service import rag_service
        
        result = await rag_service.get_collection_documents(
            collection_id=uuid.UUID(collection_id),
            page=page,
            limit=limit,
            status=status,
            db=db
        )
        
        # 응답 변환
        documents = [RAGDocumentResponse.model_validate(doc) for doc in result["documents"]]
        
        logger.info(f"문서 목록 조회 완료: 컬렉션 {collection_id}, {len(documents)}개 문서")
        
        return RAGDocumentListResponse(
            documents=documents,
            total=result["total"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 목록 조회에 실패했습니다")


@router.post("/collections/{collection_id}/documents/upload", response_model=RAGDocumentUploadResponse)
async def upload_document(
    collection_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """문서 업로드 및 처리 시작"""
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (MEMBER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.MEMBER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="문서 업로드 권한이 없습니다")
        
        # 파일 유효성 검사
        from src.services.rag_service import rag_service
        
        # 파일 크기 가져오기 (UploadFile은 size 속성이 없을 수 있음)
        file_size = getattr(file, 'size', None)
        if file_size is None:
            # 파일 내용을 읽어서 크기 계산
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)  # 파일 포인터를 처음으로 되돌림
        
        validation_result = rag_service.validate_file(file.filename, file_size)
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"파일 유효성 검사 실패: {'; '.join(validation_result['errors'])}"
            )
        
        # 업로드 디렉토리 생성
        config = get_rag_config()
        upload_dir_path = config.get_collection_upload_dir(collection.workspace_id, collection.name)
        from pathlib import Path
        upload_dir = Path(upload_dir_path)
        
        # 파일 저장
        import tempfile
        import shutil
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_file_path = tmp_file.name
        
        try:
            # RAG Service로 문서 처리
            document = await rag_service.upload_and_process_document(
                collection=collection,
                file_path=temp_file_path,
                original_filename=file.filename,
                uploaded_by=current_user.id,
                db=db
            )
            
            logger.info(f"문서 업로드 시작: {document.id} (파일: {file.filename})")
            
            return RAGDocumentUploadResponse(
                document_id=document.id,
                filename=document.filename,
                file_size=document.file_size,
                status=document.status,
                message="문서 업로드가 시작되었습니다. 처리 상태를 확인해주세요."
            )
            
        finally:
            # 임시 파일 정리
            import os
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 업로드 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 업로드에 실패했습니다")


@router.delete("/collections/{collection_id}/documents/{document_id}")
async def delete_document(
    collection_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """문서 삭제 (파일 및 벡터 데이터 포함)"""
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (MEMBER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.MEMBER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="문서 삭제 권한이 없습니다")
        
        # 문서 조회
        document_query = select(RAGDocument).where(
            and_(
                RAGDocument.id == uuid.UUID(document_id),
                RAGDocument.collection_id == uuid.UUID(collection_id)
            )
        )
        document_result = await db.execute(document_query)
        document = document_result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
        
        # RAG Service로 문서 삭제
        from src.services.rag_service import rag_service
        
        success = await rag_service.delete_document(
            document=document,
            collection=collection,
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="문서 삭제에 실패했습니다")
        
        logger.info(f"문서 삭제 완료: {document_id} (사용자: {current_user.id})")
        
        return {"message": "문서가 성공적으로 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 삭제에 실패했습니다")


# ============ RAG Search APIs (스켈레톤) ============

@router.post("/collections/{collection_id}/search", response_model=RAGSearchResponse)
async def search_collection(
    collection_id: str,
    search_request: RAGSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG 검색 실행"""
    
    logger.info(f"RAG 검색 요청 시작: 컬렉션 {collection_id}, 쿼리: {search_request.query}")
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (VIEWER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="검색 권한이 없습니다")
        
        # 컬렉션 상태 확인
        if collection.status != "active":
            raise HTTPException(status_code=400, detail="비활성 컬렉션에서는 검색할 수 없습니다")
        
        if collection.document_count == 0:
            raise HTTPException(status_code=400, detail="문서가 없는 컬렉션에서는 검색할 수 없습니다")
        
        # RAG Service로 검색 실행
        from src.services.rag_service import rag_service
        
        search_result = await rag_service.search_collection(
            collection=collection,
            query=search_request.query,
            user_id=current_user.id,
            include_metadata=search_request.include_metadata,
            db=db
        )
        
        # 검색 ID 생성 (검색 기록에서 사용)
        search_id = uuid.uuid4()
        
        logger.info(f"RAG 검색 완료: 컬렉션 {collection_id}, 쿼리: {search_request.query[:50]}...")
        
        return RAGSearchResponse(
            search_id=search_id,
            result=search_result,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG 검색 실패 - 상세 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"검색에 실패했습니다: {str(e)}")


@router.get("/collections/{collection_id}/search/history", response_model=RAGSearchHistoryListResponse)
async def get_search_history(
    collection_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_filter: bool = Query(False, description="현재 사용자 기록만 조회"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """검색 기록 조회"""
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (VIEWER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="검색 기록 조회 권한이 없습니다")
        
        # RAG Service로 검색 기록 조회
        from src.services.rag_service import rag_service
        
        # 사용자 필터 설정 (user_filter가 True면 현재 사용자만, False면 모든 사용자)
        user_id_filter = current_user.id if user_filter else None
        
        result = await rag_service.get_search_history(
            collection_id=uuid.UUID(collection_id),
            page=page,
            limit=limit,
            user_id=user_id_filter,
            db=db
        )
        
        # 응답 변환
        history = [RAGSearchHistoryResponse.model_validate(item) for item in result["history"]]
        
        logger.info(f"검색 기록 조회 완료: 컬렉션 {collection_id}, {len(history)}개 기록")
        
        return RAGSearchHistoryListResponse(
            history=history,
            total=result["total"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검색 기록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="검색 기록 조회에 실패했습니다")


# ============ Statistics APIs ============

@router.get("/workspaces/{workspace_id}/stats", response_model=RAGWorkspaceStats)
async def get_workspace_stats(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """워크스페이스 RAG 통계 조회"""
    
    try:
        # 권한 확인 (VIEWER 이상 필요)
        has_permission = await check_workspace_permission(
            workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="워크스페이스 통계 조회 권한이 없습니다")
        
        # RAG Service로 통계 조회
        from src.services.rag_service import rag_service
        
        stats = await rag_service.get_workspace_stats(workspace_id, db)
        
        logger.info(f"워크스페이스 통계 조회 완료: {workspace_id}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"워크스페이스 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회에 실패했습니다")


@router.get("/collections/{collection_id}/stats", response_model=RAGCollectionStats)
async def get_collection_stats(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """컬렉션 통계 조회"""
    
    try:
        # 컬렉션 조회 및 권한 확인
        collection_query = select(RAGCollection).where(RAGCollection.id == uuid.UUID(collection_id))
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="컬렉션을 찾을 수 없습니다")
        
        # 권한 확인 (VIEWER 이상 필요)
        has_permission = await check_workspace_permission(
            collection.workspace_id, current_user, WorkspacePermissionLevel.VIEWER, db
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="컬렉션 통계 조회 권한이 없습니다")
        
        # RAG Service로 통계 조회
        from src.services.rag_service import rag_service
        
        stats = await rag_service.get_collection_stats(uuid.UUID(collection_id), db)
        
        logger.info(f"컬렉션 통계 조회 완료: {collection_id}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"컬렉션 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회에 실패했습니다")


# ============ User Feedback APIs ============

@router.post("/search/{search_history_id}/feedback")
async def submit_user_feedback(
    search_history_id: str,
    feedback_request: RAGUserFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """검색 결과에 대한 사용자 피드백 제출"""
    
    try:
        # 검색 기록 조회
        history_query = select(RAGSearchHistory).where(RAGSearchHistory.id == uuid.UUID(search_history_id))
        history_result = await db.execute(history_query)
        search_history = history_result.scalar_one_or_none()
        
        if not search_history:
            raise HTTPException(status_code=404, detail="검색 기록을 찾을 수 없습니다")
        
        # 피드백 제출자 확인 (본인 검색 기록만 피드백 가능)
        if search_history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="본인의 검색 기록에만 피드백을 남길 수 있습니다")
        
        # 피드백 업데이트
        if feedback_request.rating is not None:
            search_history.user_rating = feedback_request.rating
        if feedback_request.feedback is not None:
            search_history.user_feedback = feedback_request.feedback
        
        await db.commit()
        
        logger.info(f"사용자 피드백 제출 완료: 검색 기록 {search_history_id}")
        
        return {"message": "피드백이 성공적으로 제출되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"피드백 제출 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 제출에 실패했습니다")