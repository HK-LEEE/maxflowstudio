"""
Flow Template Service
템플릿 관련 비즈니스 로직
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from src.models.flow_template import FlowTemplate
from src.models.flow import Flow
from src.schemas.flow_template import (
    CreateFlowTemplateRequest,
    UpdateFlowTemplateRequest,
    FlowTemplateResponse,
    FlowTemplateListItem,
    SaveAsTemplateRequest
)
from src.core.exceptions import NotFoundError, ValidationError, PermissionError
import logging

logger = logging.getLogger(__name__)


class FlowTemplateService:
    """템플릿 관리 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_template(
        self, 
        template_data: CreateFlowTemplateRequest, 
        created_by: UUID
    ) -> FlowTemplateResponse:
        """새 템플릿 생성"""
        try:
            # 같은 이름의 템플릿이 있는지 확인
            existing = await self._get_template_by_name(template_data.name)
            if existing:
                raise ValidationError(f"이미 같은 이름의 템플릿이 존재합니다: {template_data.name}")
            
            # 템플릿 생성
            template = FlowTemplate(
                name=template_data.name,
                description=template_data.description,
                category=template_data.category or "General",
                definition=template_data.definition,
                thumbnail=template_data.thumbnail,
                is_public=template_data.is_public,
                created_by=created_by
            )
            
            self.db.add(template)
            await self.db.commit()
            await self.db.refresh(template)
            
            logger.info(f"템플릿 생성 완료: {template.name} (ID: {template.id})")
            return FlowTemplateResponse.model_validate(template)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"템플릿 생성 실패: {str(e)}")
            raise
    
    async def get_template(self, template_id: UUID) -> FlowTemplateResponse:
        """템플릿 상세 조회"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")
        
        return FlowTemplateResponse.model_validate(template)
    
    async def get_templates(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_public: Optional[bool] = None,
        created_by: Optional[UUID] = None
    ) -> Tuple[List[FlowTemplateListItem], int]:
        """템플릿 목록 조회"""
        try:
            # 기본 쿼리 구성
            query = select(FlowTemplate)
            count_query = select(func.count(FlowTemplate.id))
            
            # 필터 조건 추가
            conditions = []
            
            if category:
                conditions.append(FlowTemplate.category == category)
            
            if search:
                search_condition = or_(
                    FlowTemplate.name.ilike(f"%{search}%"),
                    FlowTemplate.description.ilike(f"%{search}%")
                )
                conditions.append(search_condition)
            
            if is_public is not None:
                conditions.append(FlowTemplate.is_public == is_public)
            
            if created_by:
                conditions.append(FlowTemplate.created_by == created_by)
            
            # 조건 적용
            if conditions:
                condition = and_(*conditions)
                query = query.where(condition)
                count_query = count_query.where(condition)
            
            # 정렬 및 페이징
            query = query.order_by(FlowTemplate.created_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # 실행
            result = await self.db.execute(query)
            templates = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            # 응답 변환
            items = [FlowTemplateListItem.model_validate(template) for template in templates]
            
            logger.info(f"템플릿 목록 조회: {len(items)}개 (총 {total}개)")
            return items, total
            
        except Exception as e:
            logger.error(f"템플릿 목록 조회 실패: {str(e)}")
            raise
    
    async def update_template(
        self,
        template_id: UUID,
        template_data: UpdateFlowTemplateRequest,
        user_id: UUID,
        is_admin: bool = False
    ) -> FlowTemplateResponse:
        """템플릿 업데이트"""
        try:
            template = await self._get_template_by_id(template_id)
            if not template:
                raise NotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")
            
            # 권한 확인 (관리자이거나 생성자인 경우만 수정 가능)
            if not is_admin and template.created_by != user_id:
                raise PermissionError("템플릿을 수정할 권한이 없습니다")
            
            # 이름 중복 확인 (이름이 변경된 경우)
            if template_data.name and template_data.name != template.name:
                existing = await self._get_template_by_name(template_data.name)
                if existing and existing.id != template_id:
                    raise ValidationError(f"이미 같은 이름의 템플릿이 존재합니다: {template_data.name}")
            
            # 필드 업데이트
            update_fields = template_data.model_dump(exclude_unset=True)
            for field, value in update_fields.items():
                setattr(template, field, value)
            
            await self.db.commit()
            await self.db.refresh(template)
            
            logger.info(f"템플릿 업데이트 완료: {template.name} (ID: {template.id})")
            return FlowTemplateResponse.model_validate(template)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"템플릿 업데이트 실패: {str(e)}")
            raise
    
    async def delete_template(
        self,
        template_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> bool:
        """템플릿 삭제"""
        try:
            template = await self._get_template_by_id(template_id)
            if not template:
                raise NotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")
            
            # 권한 확인
            if not is_admin and template.created_by != user_id:
                raise PermissionError("템플릿을 삭제할 권한이 없습니다")
            
            await self.db.delete(template)
            await self.db.commit()
            
            logger.info(f"템플릿 삭제 완료: {template.name} (ID: {template.id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"템플릿 삭제 실패: {str(e)}")
            raise
    
    async def save_flow_as_template(
        self,
        flow_id: UUID,
        template_data: SaveAsTemplateRequest,
        created_by: UUID
    ) -> FlowTemplateResponse:
        """Flow를 템플릿으로 저장"""
        try:
            # Flow 조회
            flow_query = select(Flow).where(Flow.id == flow_id)
            result = await self.db.execute(flow_query)
            flow = result.scalar_one_or_none()
            
            if not flow:
                raise NotFoundError(f"Flow를 찾을 수 없습니다: {flow_id}")
            
            # Flow 정의가 있는지 확인
            if not flow.definition:
                raise ValidationError("Flow 정의가 없어 템플릿으로 저장할 수 없습니다")
            
            # 템플릿 생성 요청 데이터 구성
            create_request = CreateFlowTemplateRequest(
                name=template_data.name,
                description=template_data.description or f"Flow '{flow.name}'에서 생성된 템플릿",
                category=template_data.category,
                definition=flow.definition,
                thumbnail=template_data.thumbnail,
                is_public=template_data.is_public
            )
            
            return await self.create_template(create_request, created_by)
            
        except Exception as e:
            logger.error(f"Flow를 템플릿으로 저장 실패: {str(e)}")
            raise
    
    async def increment_usage(self, template_id: UUID) -> bool:
        """템플릿 사용 횟수 증가"""
        try:
            template = await self._get_template_by_id(template_id)
            if not template:
                return False
            
            template.usage_count += 1
            await self.db.commit()
            
            logger.info(f"템플릿 사용 횟수 증가: {template.name} ({template.usage_count}회)")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"템플릿 사용 횟수 증가 실패: {str(e)}")
            return False
    
    async def get_categories(self) -> Dict[str, int]:
        """템플릿 카테고리 목록과 개수 조회"""
        try:
            query = select(
                FlowTemplate.category,
                func.count(FlowTemplate.id).label('count')
            ).where(
                FlowTemplate.is_public == True
            ).group_by(
                FlowTemplate.category
            ).order_by(
                FlowTemplate.category
            )
            
            result = await self.db.execute(query)
            categories = {}
            
            for category, count in result:
                categories[category or "General"] = count
            
            logger.info(f"카테고리 조회 완료: {len(categories)}개")
            return categories
            
        except Exception as e:
            logger.error(f"카테고리 조회 실패: {str(e)}")
            return {}
    
    async def get_template_stats(self) -> dict:
        """템플릿 통계 조회"""
        try:
            # 전체 템플릿 수
            total_query = select(func.count(FlowTemplate.id))
            total_result = await self.db.execute(total_query)
            total_templates = total_result.scalar() or 0
            
            # 공개 템플릿 수
            public_query = select(func.count(FlowTemplate.id)).where(FlowTemplate.is_public == True)
            public_result = await self.db.execute(public_query)
            public_templates = public_result.scalar() or 0
            
            # 총 사용 횟수
            usage_query = select(func.sum(FlowTemplate.usage_count))
            usage_result = await self.db.execute(usage_query)
            total_usage = usage_result.scalar() or 0
            
            # 카테고리별 통계
            category_query = select(
                FlowTemplate.category,
                func.count(FlowTemplate.id).label('count')
            ).group_by(FlowTemplate.category)
            category_result = await self.db.execute(category_query)
            category_stats = {row.category: row.count for row in category_result}
            
            return {
                "total_templates": total_templates,
                "public_templates": public_templates,
                "private_templates": total_templates - public_templates,
                "total_usage": total_usage,
                "category_stats": category_stats
            }
            
        except Exception as e:
            logger.error(f"템플릿 통계 조회 실패: {str(e)}")
            raise
    
    async def _get_template_by_id(self, template_id: UUID) -> Optional[FlowTemplate]:
        """ID로 템플릿 조회 (내부용)"""
        query = select(FlowTemplate).where(FlowTemplate.id == template_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_template_by_name(self, name: str) -> Optional[FlowTemplate]:
        """이름으로 템플릿 조회 (내부용)"""
        query = select(FlowTemplate).where(FlowTemplate.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()