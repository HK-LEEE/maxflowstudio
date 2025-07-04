"""
Workspace management endpoints
Flow: Workspace CRUD -> Permission management -> Flow organization
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.workspace import WorkspaceType
from src.models.workspace_permission import PermissionType
from src.models.user import User
from src.services.workspace_service import workspace_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    """Request to create a new workspace."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: WorkspaceType
    group_id: Optional[str] = None


class UpdateWorkspaceRequest(BaseModel):
    """Request to update an existing workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str]
    type: WorkspaceType
    creator_user_id: str
    group_id: Optional[str]
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    user_permission: Optional[PermissionType] = None
    flow_count: int = 0


class AddFlowToWorkspaceRequest(BaseModel):
    """Request to add flow to workspace."""
    flow_id: str
    workspace_id: str


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Create a new workspace."""
    
    # Validate group workspace requirements
    if request.type == WorkspaceType.GROUP:
        if not request.group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group ID is required for group workspaces"
            )
        
        # Check if user belongs to the group
        if current_user.group_id != request.group_id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create workspaces for your own group"
            )
    
    try:
        workspace = await workspace_service.create_workspace(
            db=db,
            name=request.name,
            creator_user_id=current_user.id,
            workspace_type=request.type,
            description=request.description,
            group_id=request.group_id
        )
        
        # Get user permission for response
        user_permission = await workspace_service.get_user_permission(
            db, workspace.id, current_user.id, current_user.group_id
        )
        
        response = WorkspaceResponse.model_validate(workspace)
        response.user_permission = user_permission
        response.flow_count = len(workspace.flow_mappings) if workspace.flow_mappings else 0
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workspace: {str(e)}"
        )


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[WorkspaceResponse]:
    """List workspaces accessible to the current user."""
    
    try:
        workspaces = await workspace_service.get_user_workspaces(
            db=db,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        response_list = []
        for workspace in workspaces:
            # Get user permission for each workspace
            user_permission = await workspace_service.get_user_permission(
                db, workspace.id, current_user.id, current_user.group_id
            )
            
            # Create response using model_validate (no manual datetime conversion needed)
            response = WorkspaceResponse.model_validate(workspace)
            response.user_permission = user_permission
            response.flow_count = len(workspace.flow_mappings) if workspace.flow_mappings else 0
            
            response_list.append(response)
        
        return response_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workspaces: {str(e)}"
        )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Get workspace by ID."""
    
    workspace = await workspace_service.get_workspace_by_id(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        group_id=current_user.group_id,
        is_admin=current_user.is_superuser
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    
    # Get user permission
    user_permission = await workspace_service.get_user_permission(
        db, workspace.id, current_user.id, current_user.group_id
    )
    
    response = WorkspaceResponse.model_validate(workspace)
    response.user_permission = user_permission
    response.flow_count = len(workspace.flow_mappings) if workspace.flow_mappings else 0
    
    return response


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Update workspace."""
    
    workspace = await workspace_service.update_workspace(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        is_admin=current_user.is_superuser
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or insufficient permissions"
        )
    
    # Get user permission
    user_permission = await workspace_service.get_user_permission(
        db, workspace.id, current_user.id, current_user.group_id
    )
    
    response = WorkspaceResponse.model_validate(workspace)
    response.user_permission = user_permission
    response.flow_count = len(workspace.flow_mappings) if workspace.flow_mappings else 0
    
    return response


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete workspace."""
    
    success = await workspace_service.delete_workspace(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        is_admin=current_user.is_superuser
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or insufficient permissions"
        )
    
    return {"message": "Workspace deleted successfully"}


@router.post("/flows/assign")
async def add_flow_to_workspace(
    request: AddFlowToWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Add flow to workspace."""
    
    success = await workspace_service.add_flow_to_workspace(
        db=db,
        flow_id=request.flow_id,
        workspace_id=request.workspace_id,
        user_id=current_user.id,
        is_admin=current_user.is_superuser
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add flow to workspace. Check permissions and flow ownership."
        )
    
    return {"message": "Flow added to workspace successfully"}


@router.get("/{workspace_id}/flows")
async def get_workspace_flows(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get flows in a workspace."""
    
    # Check if user has access to workspace
    workspace = await workspace_service.get_workspace_by_id(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        group_id=current_user.group_id,
        is_admin=current_user.is_superuser
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    
    # Return flows from the workspace
    flows = []
    if workspace.flow_mappings:
        for flow_map in workspace.flow_mappings:
            if flow_map.flow:
                flows.append({
                    "id": flow_map.flow.id,
                    "name": flow_map.flow.name,
                    "description": flow_map.flow.description,
                    "current_version": flow_map.flow.current_version,
                    "created_at": flow_map.flow.created_at.isoformat(),
                    "updated_at": flow_map.flow.updated_at.isoformat(),
                    "workspace_id": workspace_id
                })
    
    return flows


@router.get("/{workspace_id}/permission")
async def get_user_workspace_permission(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's permission level for a workspace."""
    
    permission = await workspace_service.get_user_permission(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        group_id=current_user.group_id
    )
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No permission found for this workspace"
        )
    
    return {
        "workspace_id": workspace_id,
        "user_id": current_user.id,
        "permission": permission,
        "is_admin": current_user.is_superuser
    }


# Admin-only workspace permission management endpoints
from src.models.workspace_mapping import WorkspaceUserMapping, WorkspaceGroupMapping, WorkspacePermissionLevel
from src.models.group import Group


def safe_uuid_convert(id_value: str) -> uuid.UUID:
    """
    Safely convert an ID string to UUID format.
    Handles both UUID strings and integer strings from Auth Server.
    
    Args:
        id_value: String ID that could be UUID format or integer
        
    Returns:
        UUID object
        
    Raises:
        ValueError: If the ID cannot be converted to a valid UUID
    """
    if not id_value:
        raise ValueError("ID value cannot be empty")
    
    # Try to parse as UUID first
    try:
        return uuid.UUID(id_value)
    except ValueError:
        # If not a valid UUID, check if it's an integer
        try:
            int_id = int(id_value)
            # Convert integer to UUID format by padding with zeros
            # e.g., "1" becomes "00000000-0000-0000-0000-000000000001"
            uuid_str = f"{int_id:032d}"
            formatted_uuid = f"{uuid_str[:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"
            return uuid.UUID(formatted_uuid)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert '{id_value}' to UUID format")


class WorkspacePermissionAssignmentRequest(BaseModel):
    """Request to assign permission to a workspace."""
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    permission_level: WorkspacePermissionLevel
    
    def validate_assignment(self):
        if not self.user_id and not self.group_id:
            raise ValueError("Either user_id or group_id must be provided")
        if self.user_id and self.group_id:
            raise ValueError("Cannot assign both user_id and group_id")


@router.post("/{workspace_id}/permissions")
async def assign_workspace_permission(
    workspace_id: str,
    assignment: WorkspacePermissionAssignmentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """관리자 전용: 워크스페이스에 사용자/그룹 권한 부여"""
    
    # Admin 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    # 입력 검증
    try:
        assignment.validate_assignment()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 워크스페이스 조회
    workspace = await workspace_service.get_workspace_by_id(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        group_id=current_user.group_id,
        is_admin=True
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if assignment.user_id:
        # 사용자 권한 할당
        from sqlalchemy import select
        
        # 사용자 존재 확인
        user_query = select(User).where(User.id == assignment.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 기존 매핑 확인
        existing_query = select(WorkspaceUserMapping).where(
            WorkspaceUserMapping.workspace_id == workspace_id,
            WorkspaceUserMapping.user_id == assignment.user_id
        )
        existing_result = await db.execute(existing_query)
        existing_mapping = existing_result.scalar_one_or_none()
        
        if existing_mapping:
            # 기존 권한 업데이트
            existing_mapping.permission_level = assignment.permission_level
            existing_mapping.assigned_by = current_user.id
            existing_mapping.assigned_at = datetime.utcnow()
            existing_mapping.updated_at = datetime.utcnow()
        else:
            # 새 매핑 생성
            new_mapping = WorkspaceUserMapping(
                workspace_id=workspace_id,
                user_id=assignment.user_id,
                permission_level=assignment.permission_level,
                assigned_by=current_user.id
            )
            db.add(new_mapping)
        
        await db.commit()
        
        return {
            "message": f"User permission {assignment.permission_level.value} assigned successfully",
            "workspace_id": workspace_id,
            "user_id": assignment.user_id,
            "permission_level": assignment.permission_level.value
        }
    
    elif assignment.group_id:
        # 그룹 권한 할당
        from sqlalchemy import select
        
        # 그룹 존재 확인
        try:
            group_uuid = safe_uuid_convert(assignment.group_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid group ID format: {str(e)}"
            )
        
        group_query = select(Group).where(Group.id == group_uuid)
        group_result = await db.execute(group_query)
        group = group_result.scalar_one_or_none()
        
        # If group not found locally, try to sync from Auth Server
        if not group:
            logger.info(
                f"Group {assignment.group_id} not found locally, attempting sync from Auth Server",
                group_id=assignment.group_id,
                workspace_id=workspace_id
            )
            
            try:
                from src.services.group_sync_service import ensure_group_exists
                
                # Extract JWT token from request to authenticate with Auth Server
                auth_token = None
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    auth_token = auth_header.split(" ")[1]
                    logger.debug(f"Extracted auth token for group sync (length: {len(auth_token)})")
                else:
                    logger.warning("No authorization header found for group sync")
                
                logger.info(f"Calling ensure_group_exists for group {assignment.group_id}")
                group = await ensure_group_exists(assignment.group_id, auth_token)
                
                if not group:
                    logger.error(
                        f"Group {assignment.group_id} not found on Auth Server after sync attempt",
                        group_id=assignment.group_id,
                        auth_token_present=bool(auth_token)
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Group {assignment.group_id} not found on Auth Server. Please check if the group exists and you have access to it."
                    )
                
                logger.info(
                    f"Successfully synced group from Auth Server",
                    group_id=str(group.id),
                    group_name=group.name,
                    workspace_id=workspace_id
                )
                
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as sync_error:
                logger.error(
                    f"Unexpected error during group sync",
                    group_id=assignment.group_id,
                    error_type=type(sync_error).__name__,
                    error_message=str(sync_error),
                    workspace_id=workspace_id
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to sync group {assignment.group_id} from Auth Server: {str(sync_error)}"
                )
        
        # 기존 매핑 확인
        existing_query = select(WorkspaceGroupMapping).where(
            WorkspaceGroupMapping.workspace_id == workspace_id,
            WorkspaceGroupMapping.group_id == group_uuid
        )
        existing_result = await db.execute(existing_query)
        existing_mapping = existing_result.scalar_one_or_none()
        
        if existing_mapping:
            # 기존 권한 업데이트
            existing_mapping.permission_level = assignment.permission_level
            existing_mapping.assigned_by = current_user.id
            existing_mapping.assigned_at = datetime.utcnow()
            existing_mapping.updated_at = datetime.utcnow()
        else:
            # 새 매핑 생성
            new_mapping = WorkspaceGroupMapping(
                workspace_id=workspace_id,
                group_id=group_uuid,
                permission_level=assignment.permission_level,
                assigned_by=current_user.id
            )
            db.add(new_mapping)
        
        await db.commit()
        
        return {
            "message": f"Group permission {assignment.permission_level.value} assigned successfully",
            "workspace_id": workspace_id,
            "group_id": assignment.group_id,
            "permission_level": assignment.permission_level.value
        }


@router.get("/{workspace_id}/permissions")
async def get_workspace_permissions(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """관리자 전용: 워크스페이스의 모든 권한 조회"""
    
    # Admin 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    from sqlalchemy import select
    
    # 사용자 권한 조회
    user_mappings_query = select(
        WorkspaceUserMapping, User.username, User.email
    ).join(User, WorkspaceUserMapping.user_id == User.id).where(
        WorkspaceUserMapping.workspace_id == workspace_id
    )
    user_mappings_result = await db.execute(user_mappings_query)
    user_mappings = user_mappings_result.all()
    
    # 그룹 권한 조회
    group_mappings_query = select(
        WorkspaceGroupMapping, Group.name
    ).join(Group, WorkspaceGroupMapping.group_id == Group.id).where(
        WorkspaceGroupMapping.workspace_id == workspace_id
    )
    group_mappings_result = await db.execute(group_mappings_query)
    group_mappings = group_mappings_result.all()
    
    return {
        "workspace_id": workspace_id,
        "user_permissions": [
            {
                "mapping_id": str(mapping.id),
                "user_id": mapping.user_id,
                "username": username,
                "email": email,
                "permission_level": mapping.permission_level.value,
                "assigned_at": mapping.assigned_at.isoformat() if mapping.assigned_at else None,
                "assigned_by": mapping.assigned_by
            }
            for mapping, username, email in user_mappings
        ],
        "group_permissions": [
            {
                "mapping_id": str(mapping.id),
                "group_id": str(mapping.group_id),
                "group_name": group_name,
                "permission_level": mapping.permission_level.value,
                "assigned_at": mapping.assigned_at.isoformat() if mapping.assigned_at else None,
                "assigned_by": mapping.assigned_by
            }
            for mapping, group_name in group_mappings
        ]
    }


@router.delete("/{workspace_id}/permissions/{mapping_type}/{mapping_id}")
async def remove_workspace_permission(
    workspace_id: str,
    mapping_type: str,  # 'user' or 'group'
    mapping_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """관리자 전용: 워크스페이스 권한 제거"""
    
    # Admin 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    from sqlalchemy import select, delete
    
    if mapping_type == 'user':
        # 사용자 매핑 삭제
        try:
            mapping_uuid = safe_uuid_convert(mapping_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mapping ID format: {str(e)}"
            )
        
        mapping_query = select(WorkspaceUserMapping).where(
            WorkspaceUserMapping.id == mapping_uuid,
            WorkspaceUserMapping.workspace_id == workspace_id
        )
        mapping_result = await db.execute(mapping_query)
        mapping = mapping_result.scalar_one_or_none()
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User mapping not found"
            )
        
        await db.delete(mapping)
        await db.commit()
        
        return {"message": "User permission removed successfully"}
    
    elif mapping_type == 'group':
        # 그룹 매핑 삭제
        try:
            mapping_uuid = safe_uuid_convert(mapping_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mapping ID format: {str(e)}"
            )
        
        mapping_query = select(WorkspaceGroupMapping).where(
            WorkspaceGroupMapping.id == mapping_uuid,
            WorkspaceGroupMapping.workspace_id == workspace_id
        )
        mapping_result = await db.execute(mapping_query)
        mapping = mapping_result.scalar_one_or_none()
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group mapping not found"
            )
        
        await db.delete(mapping)
        await db.commit()
        
        return {"message": "Group permission removed successfully"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mapping_type. Must be 'user' or 'group'"
        )