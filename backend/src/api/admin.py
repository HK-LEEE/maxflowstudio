"""
Admin API endpoints
관리자 전용 사용자 및 그룹 관리 API
"""

import uuid
import httpx
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.user import User
from src.models.group import Group
from src.models.workspace import Workspace
from src.models.workspace_mapping import (
    WorkspaceUserMapping, 
    WorkspaceGroupMapping, 
    WorkspacePermissionLevel
)
from src.services.group_sync_service import group_sync_service, sync_groups_from_auth_server
from src.config.settings import get_settings
import structlog

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


async def call_auth_server_api(endpoint: str, token: str) -> dict:
    """Auth Server API를 호출하는 헬퍼 함수"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVER_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Auth server API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Auth server error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Auth server connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Auth server is unavailable"
        )


def extract_token_from_request(request: Request) -> str:
    """Request에서 JWT 토큰을 추출하는 함수"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return auth_header.split(" ")[1]


def map_auth_user_to_response(auth_user: dict) -> dict:
    """Auth Server의 UserListResponse를 FlowStudio의 UserResponse로 매핑"""
    return {
        "id": auth_user["id"],
        "username": auth_user.get("display_name") or auth_user["real_name"],
        "email": auth_user["email"],
        "full_name": auth_user["real_name"],
        "group_id": auth_user.get("group", {}).get("id") if auth_user.get("group") else None,
        "is_active": auth_user["is_active"],
        "is_superuser": auth_user["is_admin"],
        "created_at": auth_user["created_at"],
        "updated_at": auth_user["created_at"]  # Auth server doesn't have updated_at
    }


def map_auth_group_to_response(auth_group: dict) -> dict:
    """Auth Server의 GroupDetailResponse를 FlowStudio의 GroupResponse로 매핑"""
    return {
        "id": auth_group["id"],
        "name": auth_group["name"],
        "description": auth_group.get("description"),
        "is_active": True,  # Auth server doesn't have is_active field
        "is_system_group": False,  # Auth server doesn't have is_system_group field
        "member_count": auth_group.get("users_count", 0),
        "workspace_count": 0,  # Will calculate separately
        "created_at": auth_group["created_at"],
        "updated_at": auth_group["created_at"],  # Auth server doesn't have updated_at
        "created_by": auth_group["created_by"]
    }


# Pydantic schemas
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_system_group: bool
    member_count: int
    workspace_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    group_id: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspacePermissionAssignment(BaseModel):
    workspace_id: str
    permission_level: WorkspacePermissionLevel


# Admin-only decorator
def admin_required(current_user: User = Depends(get_current_user)):
    """관리자 권한 확인"""
    logger.info("Admin access attempt", user_id=current_user.id, is_superuser=current_user.is_superuser)
    if not current_user.is_superuser:
        logger.warning("Non-admin user attempted admin access", user_id=current_user.id)
        raise HTTPException(
            status_code=403, 
            detail="Admin privileges required"
        )
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(admin_required),
    request: Request = None
):
    """사용자 목록 조회 (Auth Server에서 가져옴)"""
    
    try:
        # Request에서 JWT 토큰 추출
        token = extract_token_from_request(request)
        
        # Auth Server에서 사용자 목록 조회
        auth_users = await call_auth_server_api("/admin/users", token)
        
        logger.info(f"Received {len(auth_users)} users from auth server")
        
        # Auth Server 응답을 FlowStudio 형식으로 변환
        users = []
        for auth_user in auth_users:
            try:
                mapped_user = map_auth_user_to_response(auth_user)
                
                # 클라이언트 사이드 필터링 (Auth Server API가 필터링을 지원하지 않는 경우)
                if search:
                    search_lower = search.lower()
                    if not (
                        search_lower in mapped_user["username"].lower() or
                        search_lower in mapped_user["email"].lower() or
                        search_lower in mapped_user["full_name"].lower()
                    ):
                        continue
                
                if group_id and mapped_user["group_id"] != group_id:
                    continue
                    
                if is_active is not None and mapped_user["is_active"] != is_active:
                    continue
                
                users.append(mapped_user)
                
            except Exception as mapping_error:
                logger.warning(f"Failed to map user {auth_user.get('id', 'unknown')}: {str(mapping_error)}")
                continue
        
        # 페이지네이션 적용
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_users = users[start_idx:end_idx]
        
        logger.info(f"Returning {len(paginated_users)} users after filtering and pagination")
        return [UserResponse.model_validate(user) for user in paginated_users]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users from auth server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/groups", response_model=List[GroupResponse])
async def get_groups(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    include_system: bool = Query(True),
    current_user: User = Depends(admin_required),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """그룹 목록 조회 (Auth Server에서 가져옴)"""
    
    try:
        # Request에서 JWT 토큰 추출
        token = extract_token_from_request(request)
        
        # Auth Server에서 그룹 목록 조회
        auth_groups = await call_auth_server_api("/admin/groups", token)
        
        logger.info(f"Received {len(auth_groups)} groups from auth server")
        
        # Auth Server 응답을 FlowStudio 형식으로 변환
        groups = []
        for auth_group in auth_groups:
            try:
                mapped_group = map_auth_group_to_response(auth_group)
                
                # 로컬 DB에서 워크스페이스 수 계산
                try:
                    workspace_count_query = select(func.count(WorkspaceGroupMapping.id)).where(
                        WorkspaceGroupMapping.group_id == uuid.UUID(mapped_group["id"])
                    )
                    workspace_count_result = await db.execute(workspace_count_query)
                    workspace_count = workspace_count_result.scalar() or 0
                    mapped_group["workspace_count"] = workspace_count
                except Exception as ws_error:
                    logger.warning(f"Failed to calculate workspace count for group {mapped_group['id']}: {str(ws_error)}")
                    mapped_group["workspace_count"] = 0
                
                # 클라이언트 사이드 필터링
                if search:
                    search_lower = search.lower()
                    if not (
                        search_lower in mapped_group["name"].lower() or
                        (mapped_group["description"] and search_lower in mapped_group["description"].lower())
                    ):
                        continue
                
                if is_active is not None and mapped_group["is_active"] != is_active:
                    continue
                    
                if not include_system and mapped_group["is_system_group"]:
                    continue
                
                groups.append(mapped_group)
                
            except Exception as mapping_error:
                logger.warning(f"Failed to map group {auth_group.get('id', 'unknown')}: {str(mapping_error)}")
                continue
        
        # 페이지네이션 적용
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_groups = groups[start_idx:end_idx]
        
        logger.info(f"Returning {len(paginated_groups)} groups after filtering and pagination")
        return [GroupResponse.model_validate(group) for group in paginated_groups]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching groups from auth server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")


@router.post("/groups", response_model=GroupResponse)
async def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """그룹 생성 (관리자 전용)"""
    
    # 중복 이름 확인
    existing_query = select(Group).where(Group.name == group_data.name)
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Group with name '{group_data.name}' already exists"
        )
    
    # 새 그룹 생성
    new_group = Group(
        id=uuid.uuid4(),
        name=group_data.name,
        description=group_data.description,
        is_active=group_data.is_active,
        is_system_group=False,
        created_by=current_user.id
    )
    
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    
    # 새 그룹이므로 멤버 수는 0
    group_dict = {
        "id": str(new_group.id),
        "name": new_group.name,
        "description": new_group.description,
        "is_active": new_group.is_active,
        "is_system_group": new_group.is_system_group,
        "member_count": 0,
        "workspace_count": new_group.workspace_count,
        "created_at": new_group.created_at,
        "updated_at": new_group.updated_at,
        "created_by": new_group.created_by
    }
    return GroupResponse(**group_dict)


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """특정 그룹 조회 (관리자 전용)"""
    
    query = select(Group).where(Group.id == uuid.UUID(group_id))
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # 실제 멤버 수 계산
    member_count_query = select(func.count(User.id)).where(User.group_id == str(group.id))
    member_count_result = await db.execute(member_count_query)
    member_count = member_count_result.scalar() or 0
    
    group_dict = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "is_system_group": group.is_system_group,
        "member_count": member_count,
        "workspace_count": group.workspace_count,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "created_by": group.created_by
    }
    return GroupResponse(**group_dict)


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """그룹 수정 (관리자 전용)"""
    
    # 그룹 조회
    query = select(Group).where(Group.id == uuid.UUID(group_id))
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # 시스템 그룹은 수정 제한
    if group.is_system_group and group_data.name:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify system group name"
        )
    
    # 이름 중복 확인 (변경하는 경우)
    if group_data.name and group_data.name != group.name:
        existing_query = select(Group).where(
            and_(
                Group.name == group_data.name,
                Group.id != group.id
            )
        )
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Group with name '{group_data.name}' already exists"
            )
    
    # 업데이트 적용
    if group_data.name is not None:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.is_active is not None:
        group.is_active = group_data.is_active
    
    group.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(group)
    
    # 실제 멤버 수 계산
    member_count_query = select(func.count(User.id)).where(User.group_id == str(group.id))
    member_count_result = await db.execute(member_count_query)
    member_count = member_count_result.scalar() or 0
    
    group_dict = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "is_system_group": group.is_system_group,
        "member_count": member_count,
        "workspace_count": group.workspace_count,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "created_by": group.created_by
    }
    return GroupResponse(**group_dict)


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """그룹 삭제 (관리자 전용)"""
    
    # 그룹 조회
    query = select(Group).where(Group.id == uuid.UUID(group_id))
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # 시스템 그룹은 삭제 불가
    if group.is_system_group:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete system group"
        )
    
    # 그룹에 속한 사용자 확인
    user_count_query = select(func.count(User.id)).where(User.group_id == str(group.id))
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar()
    
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete group with {user_count} members. Remove all members first."
        )
    
    # 그룹 삭제 (CASCADE로 관련 매핑들도 자동 삭제됨)
    await db.delete(group)
    await db.commit()
    
    return {"message": "Group deleted successfully"}


class UserGroupAssignment(BaseModel):
    group_id: str = Field(..., description="Group ID to assign user to")

@router.post("/users/{user_id}/group")
async def assign_user_to_group(
    user_id: str,
    assignment: UserGroupAssignment,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """사용자를 그룹에 할당 (관리자 전용)"""
    
    # 사용자 조회
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 그룹 조회
    group_query = select(Group).where(Group.id == uuid.UUID(assignment.group_id))
    group_result = await db.execute(group_query)
    group = group_result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if not group.is_active:
        raise HTTPException(status_code=400, detail="Cannot assign to inactive group")
    
    # 사용자 그룹 업데이트
    user.group_id = str(group.id)
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"User {user.username} assigned to group {group.name}"}


@router.delete("/users/{user_id}/group")
async def remove_user_from_group(
    user_id: str,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """사용자를 그룹에서 제거 (관리자 전용)"""
    
    # 사용자 조회
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.group_id:
        raise HTTPException(status_code=400, detail="User is not in any group")
    
    # 사용자 그룹 제거
    old_group_id = user.group_id
    user.group_id = None
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"User {user.username} removed from group"}


# Group Synchronization Endpoints

@router.post("/groups/sync")
async def sync_groups_from_auth(
    preserve_local: bool = Query(True, description="Whether to preserve local-only groups"),
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync all groups from Auth Server to local database (관리자 전용)
    
    Args:
        preserve_local: If True, keep local-only groups. If False, remove them.
    """
    try:
        stats = await sync_groups_from_auth_server(preserve_local_groups=preserve_local)
        
        return {
            "message": "Group synchronization completed successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error("Group sync failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Group synchronization failed: {str(e)}"
        )


@router.post("/groups/{group_id}/sync")
async def sync_single_group_from_auth(
    group_id: str,
    current_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync a specific group from Auth Server to local database (관리자 전용)
    """
    try:
        from src.services.group_sync_service import ensure_group_exists
        
        synced_group = await ensure_group_exists(group_id)
        
        if not synced_group:
            raise HTTPException(
                status_code=404,
                detail=f"Group {group_id} not found on Auth Server"
            )
        
        return {
            "message": f"Group {synced_group.name} synced successfully",
            "group": {
                "id": str(synced_group.id),
                "name": synced_group.name,
                "description": synced_group.description,
                "is_active": synced_group.is_active
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Single group sync failed", group_id=group_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync group {group_id}: {str(e)}"
        )


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(admin_required),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """관리자 대시보드 통계 (Auth Server 데이터 기반)"""
    
    try:
        # Request에서 JWT 토큰 추출
        token = extract_token_from_request(request)
        
        # Auth Server에서 사용자와 그룹 데이터 조회
        auth_users = await call_auth_server_api("/admin/users", token)
        auth_groups = await call_auth_server_api("/admin/groups", token)
        
        # 사용자 통계 계산
        total_users = len(auth_users)
        active_users = len([user for user in auth_users if user.get("is_active", False)])
        admin_users = len([user for user in auth_users if user.get("is_admin", False)])
        
        # 그룹 통계 계산
        total_groups = len(auth_groups)
        active_groups = total_groups  # Auth server doesn't have is_active field for groups
        
        # 워크스페이스 통계 (로컬 DB에서 조회)
        total_workspaces_query = select(func.count(Workspace.id))
        active_workspaces_query = select(func.count(Workspace.id)).where(Workspace.is_active == True)
        
        total_workspaces = (await db.execute(total_workspaces_query)).scalar() or 0
        active_workspaces = (await db.execute(active_workspaces_query)).scalar() or 0
        
        stats = {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users
            },
            "groups": {
                "total": total_groups,
                "active": active_groups
            },
            "workspaces": {
                "total": total_workspaces,
                "active": active_workspaces
            }
        }
        
        logger.info(f"Admin stats generated from auth server: {stats}")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating admin stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating admin stats: {str(e)}")