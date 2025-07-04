"""
Flow Template Schemas
템플릿 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class FlowTemplateBase(BaseModel):
    """템플릿 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="템플릿 이름")
    description: Optional[str] = Field(None, description="템플릿 설명")
    category: Optional[str] = Field("General", max_length=100, description="템플릿 카테고리")
    is_public: bool = Field(True, description="공개 여부")


class CreateFlowTemplateRequest(FlowTemplateBase):
    """템플릿 생성 요청"""
    definition: Dict[str, Any] = Field(..., description="Flow 정의 (nodes, edges)")
    thumbnail: Optional[str] = Field(None, description="썸네일 이미지 URL")
    
    @validator('definition')
    def validate_definition(cls, v):
        """Flow 정의 유효성 검사"""
        if not isinstance(v, dict):
            raise ValueError("정의는 dictionary 형태여야 합니다")
        
        # 필수 필드 확인
        required_fields = ['nodes', 'edges']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"정의에 '{field}' 필드가 필요합니다")
        
        # nodes와 edges가 리스트인지 확인
        if not isinstance(v['nodes'], list):
            raise ValueError("nodes는 리스트여야 합니다")
        if not isinstance(v['edges'], list):
            raise ValueError("edges는 리스트여야 합니다")
            
        return v


class UpdateFlowTemplateRequest(BaseModel):
    """템플릿 업데이트 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=100)
    definition: Optional[Dict[str, Any]] = Field(None)
    thumbnail: Optional[str] = Field(None)
    is_public: Optional[bool] = Field(None)
    
    @validator('definition')
    def validate_definition(cls, v):
        """Flow 정의 유효성 검사"""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("정의는 dictionary 형태여야 합니다")
            
            # 필수 필드 확인
            required_fields = ['nodes', 'edges']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"정의에 '{field}' 필드가 필요합니다")
                    
        return v


class FlowTemplateResponse(FlowTemplateBase):
    """템플릿 응답"""
    id: UUID
    definition: Dict[str, Any]
    thumbnail: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    usage_count: int
    display_name: str
    
    model_config = {"from_attributes": True}


class FlowTemplateListItem(BaseModel):
    """템플릿 목록 아이템 (간소화된 정보)"""
    id: UUID
    name: str
    description: Optional[str]
    category: Optional[str]
    thumbnail: Optional[str]
    is_public: bool
    created_at: datetime
    usage_count: int
    display_name: str
    
    model_config = {"from_attributes": True}


class FlowTemplateListResponse(BaseModel):
    """템플릿 목록 응답"""
    items: List[FlowTemplateListItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class FlowTemplateCategoryResponse(BaseModel):
    """템플릿 카테고리 응답"""
    categories: List[str]
    category_counts: Dict[str, int]


class SaveAsTemplateRequest(BaseModel):
    """템플릿으로 저장 요청"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field("General", max_length=100)
    is_public: bool = Field(True)
    thumbnail: Optional[str] = Field(None)


class SaveAsFlowRequest(BaseModel):
    """다른 이름으로 저장 요청"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    
    @validator('name')
    def validate_name(cls, v):
        """이름 유효성 검사"""
        if not v.strip():
            raise ValueError("이름은 공백일 수 없습니다")
        return v.strip()


class LoadTemplateRequest(BaseModel):
    """템플릿 로드 요청"""
    template_id: UUID = Field(..., description="로드할 템플릿 ID")
    increment_usage: bool = Field(True, description="사용 횟수 증가 여부")