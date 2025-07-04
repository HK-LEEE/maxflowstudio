"""
Flow Template API Endpoints
템플릿 관리 관련 API
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.user import User
from src.services.flow_template_service import FlowTemplateService
from src.schemas.flow_template import (
    CreateFlowTemplateRequest,
    UpdateFlowTemplateRequest,
    FlowTemplateResponse,
    FlowTemplateListResponse,
    FlowTemplateListItem,
    FlowTemplateCategoryResponse,
    SaveAsTemplateRequest,
    SaveAsFlowRequest,
    LoadTemplateRequest
)
from src.core.exceptions import NotFoundError, ValidationError, PermissionError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Flow Templates"])


@router.get("/", response_model=FlowTemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    search: Optional[str] = Query(None, description="검색어"),
    is_public: Optional[bool] = Query(None, description="공개 여부 필터"),
    my_templates: bool = Query(False, description="내 템플릿만 조회"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 목록 조회"""
    try:
        service = FlowTemplateService(db)
        
        # 내 템플릿만 조회하는 경우
        created_by = current_user.id if my_templates else None
        
        items, total = await service.get_templates(
            page=page,
            page_size=page_size,
            category=category,
            search=search,
            is_public=is_public,
            created_by=created_by
        )
        
        return FlowTemplateListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=page * page_size < total,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"템플릿 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 목록을 가져오는 중 오류가 발생했습니다"
        )


@router.get("/stats")
async def get_template_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 통계 조회 (관리자 전용)"""
    try:
        # 관리자 권한 확인
        if not current_user.is_superuser:
            raise PermissionError("관리자 권한이 필요합니다")
        
        service = FlowTemplateService(db)
        stats = await service.get_template_stats()
        
        return stats
        
    except PermissionError as e:
        logger.warning(f"템플릿 통계 조회 권한 없음: user_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 통계를 가져오는 중 오류가 발생했습니다"
        )


@router.get("/categories", response_model=FlowTemplateCategoryResponse)
async def get_template_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 카테고리 목록 조회"""
    try:
        service = FlowTemplateService(db)
        category_counts = await service.get_categories()
        
        return FlowTemplateCategoryResponse(
            categories=list(category_counts.keys()),
            category_counts=category_counts
        )
        
    except Exception as e:
        logger.error(f"카테고리 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 목록을 가져오는 중 오류가 발생했습니다"
        )


@router.get("/{template_id}", response_model=FlowTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 상세 조회"""
    try:
        service = FlowTemplateService(db)
        return await service.get_template(template_id)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿을 가져오는 중 오류가 발생했습니다"
        )


@router.post("/", response_model=FlowTemplateResponse)
async def create_template(
    template_data: CreateFlowTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 템플릿 생성 (관리자만)"""
    try:
        # 관리자 권한 확인
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="템플릿 생성 권한이 없습니다"
            )
        
        service = FlowTemplateService(db)
        return await service.create_template(template_data, current_user.id)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 생성 중 오류가 발생했습니다"
        )


@router.put("/{template_id}", response_model=FlowTemplateResponse)
async def update_template(
    template_id: UUID,
    template_data: UpdateFlowTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 업데이트"""
    try:
        service = FlowTemplateService(db)
        return await service.update_template(
            template_id=template_id,
            template_data=template_data,
            user_id=current_user.id,
            is_admin=current_user.is_superuser
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 업데이트 중 오류가 발생했습니다"
        )


@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 삭제"""
    try:
        service = FlowTemplateService(db)
        success = await service.delete_template(
            template_id=template_id,
            user_id=current_user.id,
            is_admin=current_user.is_superuser
        )
        
        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "템플릿이 성공적으로 삭제되었습니다"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="템플릿 삭제에 실패했습니다"
            )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 삭제 중 오류가 발생했습니다"
        )


@router.post("/{template_id}/load")
async def load_template(
    template_id: UUID,
    request: LoadTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """템플릿 로드 (사용 횟수 증가)"""
    try:
        service = FlowTemplateService(db)
        
        # 템플릿 조회
        template = await service.get_template(template_id)
        
        # 사용 횟수 증가
        if request.increment_usage:
            await service.increment_usage(template_id)
        
        # 템플릿 정의 반환
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "template": template.model_dump(),
                "message": "템플릿을 성공적으로 로드했습니다"
            }
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"템플릿 로드 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 로드 중 오류가 발생했습니다"
        )


@router.post("/save-from-flow/{flow_id}", response_model=FlowTemplateResponse)
async def save_flow_as_template(
    flow_id: UUID,
    template_data: SaveAsTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Flow를 템플릿으로 저장 (관리자만)"""
    try:
        # 관리자 권한 확인
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="템플릿 저장 권한이 없습니다"
            )
        
        service = FlowTemplateService(db)
        return await service.save_flow_as_template(
            flow_id=flow_id,
            template_data=template_data,
            created_by=current_user.id
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Flow를 템플릿으로 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 저장 중 오류가 발생했습니다"
        )