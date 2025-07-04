"""
Environment Variables management endpoints
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.environment_variable import (
    EnvironmentVariable, 
    EnvironmentVariableType,
    EnvironmentVariableCategory,
    EnvironmentVariableScope
)
from src.models.user import User
from src.services.workspace_service import workspace_service
from src.services.environment_service import environment_service

router = APIRouter()


# Pydantic schemas
class EnvironmentVariableCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Optional[str] = None
    description: Optional[str] = None
    var_type: EnvironmentVariableType = EnvironmentVariableType.STRING
    category: EnvironmentVariableCategory = EnvironmentVariableCategory.CUSTOM
    scope: EnvironmentVariableScope = EnvironmentVariableScope.USER
    is_secret: bool = False
    workspace_id: Optional[str] = None
    sort_order: Optional[int] = 0


class EnvironmentVariableUpdate(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = None
    description: Optional[str] = None
    var_type: Optional[EnvironmentVariableType] = None
    category: Optional[EnvironmentVariableCategory] = None
    scope: Optional[EnvironmentVariableScope] = None
    is_secret: Optional[bool] = None
    sort_order: Optional[int] = None


class EnvironmentVariableResponse(BaseModel):
    id: str
    key: str
    value: Optional[str]  # Masked for secrets
    description: Optional[str]
    var_type: EnvironmentVariableType
    category: EnvironmentVariableCategory
    scope: EnvironmentVariableScope
    is_secret: bool
    is_encrypted: bool
    is_system_managed: bool
    user_id: Optional[str]
    workspace_id: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime
    
    # Additional display fields
    category_display_name: Optional[str] = None
    scope_display_name: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[EnvironmentVariableResponse])
async def list_environment_variables(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    category: Optional[EnvironmentVariableCategory] = Query(None, description="Filter by category"),
    scope: Optional[EnvironmentVariableScope] = Query(None, description="Filter by scope"),
    include_global: bool = Query(True, description="Include user-global variables"),
    include_system: bool = Query(True, description="Include system variables"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List environment variables accessible to the current user."""
    
    query_conditions = []
    
    # Build access conditions based on scope
    access_conditions = []
    
    # User-specific variables
    if include_global:
        access_conditions.append(
            and_(
                EnvironmentVariable.user_id == current_user.id,
                EnvironmentVariable.scope == EnvironmentVariableScope.USER
            )
        )
    
    # System variables (if user is admin or include_system is True)
    if include_system and (current_user.is_superuser or include_system):
        access_conditions.append(
            EnvironmentVariable.scope == EnvironmentVariableScope.SYSTEM
        )
    
    # Workspace-specific variables
    if workspace_id:
        # Verify workspace access
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
        
        access_conditions.append(
            and_(
                EnvironmentVariable.workspace_id == workspace_id,
                EnvironmentVariable.scope == EnvironmentVariableScope.WORKSPACE
            )
        )
    
    if access_conditions:
        query_conditions.append(or_(*access_conditions))
    
    # Filter by category if specified
    if category:
        query_conditions.append(EnvironmentVariable.category == category)
    
    # Filter by scope if specified
    if scope:
        query_conditions.append(EnvironmentVariable.scope == scope)
    
    # Build and execute query
    query = select(EnvironmentVariable).where(and_(*query_conditions)).order_by(
        EnvironmentVariable.category,
        EnvironmentVariable.sort_order,
        EnvironmentVariable.key
    )
    result = await db.execute(query)
    env_vars = result.scalars().all()
    
    # Build response with display values
    response_vars = []
    for env_var in env_vars:
        var_dict = {
            "id": str(env_var.id),
            "key": env_var.key,
            "value": env_var.get_display_value(),
            "description": env_var.description,
            "var_type": env_var.var_type,
            "category": env_var.category,
            "scope": env_var.scope,
            "is_secret": env_var.is_secret,
            "is_encrypted": env_var.is_encrypted,
            "is_system_managed": env_var.is_system_managed,
            "user_id": env_var.user_id,
            "workspace_id": env_var.workspace_id,
            "sort_order": env_var.sort_order,
            "created_at": env_var.created_at,
            "updated_at": env_var.updated_at,
            "category_display_name": env_var.get_category_display_name(),
            "scope_display_name": env_var.get_scope_display_name(),
        }
        response_vars.append(EnvironmentVariableResponse(**var_dict))
    
    return response_vars


@router.post("/", response_model=EnvironmentVariableResponse)
async def create_environment_variable(
    env_var: EnvironmentVariableCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new environment variable."""
    
    # Verify workspace access if workspace_id is provided
    if env_var.workspace_id:
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=env_var.workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    # Check for duplicate key in same scope
    existing_query = select(EnvironmentVariable).where(
        and_(
            EnvironmentVariable.user_id == current_user.id,
            EnvironmentVariable.key == env_var.key,
            EnvironmentVariable.workspace_id == env_var.workspace_id
        )
    )
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail=f"Environment variable '{env_var.key}' already exists in this scope"
        )
    
    # Create new environment variable
    new_env_var = EnvironmentVariable(
        id=uuid.uuid4(),
        key=env_var.key,
        description=env_var.description,
        var_type=env_var.var_type,
        category=env_var.category,
        scope=env_var.scope,
        is_secret=env_var.is_secret,
        is_encrypted=False,
        is_system_managed=False,  # User-created variables are not system managed
        user_id=current_user.id if env_var.scope != EnvironmentVariableScope.SYSTEM else None,
        workspace_id=env_var.workspace_id if env_var.scope == EnvironmentVariableScope.WORKSPACE else None,
        sort_order=env_var.sort_order or 0,
        created_by=current_user.id,
    )
    
    # Set value using the model's encryption logic
    if env_var.value:
        new_env_var.set_value(env_var.value)
    
    db.add(new_env_var)
    await db.commit()
    await db.refresh(new_env_var)
    
    # Return response with masked value if secret
    var_dict = {
        "id": str(new_env_var.id),
        "key": new_env_var.key,
        "value": new_env_var.get_display_value(),
        "description": new_env_var.description,
        "var_type": new_env_var.var_type,
        "category": new_env_var.category,
        "scope": new_env_var.scope,
        "is_secret": new_env_var.is_secret,
        "is_encrypted": new_env_var.is_encrypted,
        "is_system_managed": new_env_var.is_system_managed,
        "user_id": new_env_var.user_id,
        "workspace_id": new_env_var.workspace_id,
        "sort_order": new_env_var.sort_order,
        "created_at": new_env_var.created_at,
        "updated_at": new_env_var.updated_at,
        "category_display_name": new_env_var.get_category_display_name(),
        "scope_display_name": new_env_var.get_scope_display_name(),
    }
    
    return EnvironmentVariableResponse(**var_dict)


@router.get("/{env_var_id}", response_model=EnvironmentVariableResponse)
async def get_environment_variable(
    env_var_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific environment variable by ID."""
    
    query = select(EnvironmentVariable).where(
        and_(
            EnvironmentVariable.id == uuid.UUID(env_var_id),
            EnvironmentVariable.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    env_var = result.scalar_one_or_none()
    
    if not env_var:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    # Return response with masked value if secret
    var_dict = {
        "id": str(env_var.id),
        "key": env_var.key,
        "value": env_var.get_display_value(),
        "description": env_var.description,
        "var_type": env_var.var_type,
        "is_secret": env_var.is_secret,
        "is_encrypted": env_var.is_encrypted,
        "user_id": env_var.user_id,
        "workspace_id": env_var.workspace_id,
        "created_at": env_var.created_at,
        "updated_at": env_var.updated_at,
    }
    
    return EnvironmentVariableResponse(**var_dict)


@router.put("/{env_var_id}", response_model=EnvironmentVariableResponse)
async def update_environment_variable(
    env_var_id: str,
    env_var_update: EnvironmentVariableUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an environment variable."""
    
    # Get existing environment variable
    query = select(EnvironmentVariable).where(
        and_(
            EnvironmentVariable.id == uuid.UUID(env_var_id),
            EnvironmentVariable.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    env_var = result.scalar_one_or_none()
    
    if not env_var:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    # Check for duplicate key if key is being changed
    if env_var_update.key and env_var_update.key != env_var.key:
        existing_query = select(EnvironmentVariable).where(
            and_(
                EnvironmentVariable.user_id == current_user.id,
                EnvironmentVariable.key == env_var_update.key,
                EnvironmentVariable.workspace_id == env_var.workspace_id,
                EnvironmentVariable.id != env_var.id
            )
        )
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"Environment variable '{env_var_update.key}' already exists in this scope"
            )
    
    # Update fields
    if env_var_update.key is not None:
        env_var.key = env_var_update.key
    if env_var_update.value is not None:
        env_var.value = env_var_update.value
    if env_var_update.description is not None:
        env_var.description = env_var_update.description
    if env_var_update.var_type is not None:
        env_var.var_type = env_var_update.var_type
    if env_var_update.is_secret is not None:
        env_var.is_secret = env_var_update.is_secret
        # TODO: Handle encryption/decryption when is_secret changes
    
    env_var.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(env_var)
    
    # Return response with masked value if secret
    var_dict = {
        "id": str(env_var.id),
        "key": env_var.key,
        "value": env_var.get_display_value(),
        "description": env_var.description,
        "var_type": env_var.var_type,
        "is_secret": env_var.is_secret,
        "is_encrypted": env_var.is_encrypted,
        "user_id": env_var.user_id,
        "workspace_id": env_var.workspace_id,
        "created_at": env_var.created_at,
        "updated_at": env_var.updated_at,
    }
    
    return EnvironmentVariableResponse(**var_dict)


@router.delete("/{env_var_id}")
async def delete_environment_variable(
    env_var_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an environment variable."""
    
    # Verify environment variable exists and belongs to user
    query = select(EnvironmentVariable).where(
        and_(
            EnvironmentVariable.id == uuid.UUID(env_var_id),
            EnvironmentVariable.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    env_var = result.scalar_one_or_none()
    
    if not env_var:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    # Delete the environment variable
    await db.delete(env_var)
    await db.commit()
    
    return {"message": "Environment variable deleted successfully"}


@router.get("/values/resolved")
async def get_resolved_environment_variables(
    workspace_id: Optional[str] = Query(None, description="Workspace context for resolution"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get resolved environment variables as key-value pairs (for actual usage)."""
    
    if workspace_id:
        # Verify workspace access
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    # Use environment service to get resolved variables
    resolved_vars = await environment_service.get_resolved_environment_variables(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id
    )
    
    return {"environment_variables": resolved_vars}


@router.get("/keys/available")
async def get_available_environment_keys(
    workspace_id: Optional[str] = Query(None, description="Workspace context for resolution"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of all available environment variable keys."""
    
    if workspace_id:
        # Verify workspace access
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    # Get available environment variable keys
    keys = await environment_service.get_available_environment_keys(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id
    )
    
    return {"keys": keys}


@router.get("/categories/list")
async def get_environment_variable_categories():
    """Get list of available environment variable categories."""
    categories = [
        {
            "value": category.value,
            "label": {
                EnvironmentVariableCategory.DATABASE: "데이터베이스",
                EnvironmentVariableCategory.AUTHENTICATION: "인증",
                EnvironmentVariableCategory.LLM_API: "AI 모델 API",
                EnvironmentVariableCategory.INFRASTRUCTURE: "인프라",
                EnvironmentVariableCategory.APPLICATION: "애플리케이션",
                EnvironmentVariableCategory.CUSTOM: "사용자 정의",
            }[category],
            "description": {
                EnvironmentVariableCategory.DATABASE: "데이터베이스 연결 및 설정",
                EnvironmentVariableCategory.AUTHENTICATION: "JWT, 인증 관련 설정",
                EnvironmentVariableCategory.LLM_API: "AI 모델 API 키 및 엔드포인트",
                EnvironmentVariableCategory.INFRASTRUCTURE: "Redis, RabbitMQ 등 인프라 설정",
                EnvironmentVariableCategory.APPLICATION: "애플리케이션 기본 설정",
                EnvironmentVariableCategory.CUSTOM: "사용자 정의 환경변수",
            }[category]
        }
        for category in EnvironmentVariableCategory
    ]
    return {"categories": categories}


@router.get("/scopes/list") 
async def get_environment_variable_scopes():
    """Get list of available environment variable scopes."""
    scopes = [
        {
            "value": scope.value,
            "label": {
                EnvironmentVariableScope.SYSTEM: "시스템",
                EnvironmentVariableScope.USER: "사용자",
                EnvironmentVariableScope.WORKSPACE: "워크스페이스",
            }[scope],
            "description": {
                EnvironmentVariableScope.SYSTEM: "시스템 전체에 적용되는 설정",
                EnvironmentVariableScope.USER: "사용자별 개인 설정",
                EnvironmentVariableScope.WORKSPACE: "워크스페이스별 설정",
            }[scope]
        }
        for scope in EnvironmentVariableScope
    ]
    return {"scopes": scopes}