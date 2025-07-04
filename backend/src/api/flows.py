"""
Flow management endpoints
Flow: Request -> Validation -> Database -> Response
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.flow import Flow, FlowVersion
from src.models.user import User
from src.models.flow_workspace_map import FlowWorkspaceMap
from src.models.workspace import Workspace
from src.services.workspace_service import workspace_service
from src.schemas.flow_template import SaveAsFlowRequest

router = APIRouter()


# Pydantic schemas
class FlowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    definition: Optional[dict] = None
    workspace_id: Optional[str] = None


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[dict] = None


class FlowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    current_version: int
    created_at: datetime
    updated_at: datetime
    user_id: str
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    definition: Optional[dict] = None  # Flow definition from latest version

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[FlowResponse])
async def list_flows(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List flows accessible to the current user, optionally filtered by workspace."""
    
    if workspace_id:
        # Get flows from specific workspace
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
        
        # Get flows in this workspace
        flows_query = select(Flow).join(FlowWorkspaceMap).join(Workspace).where(
            FlowWorkspaceMap.workspace_id == workspace_id
        )
        
    else:
        # Get all accessible flows
        if current_user.is_superuser:
            # Admin can see all flows
            flows_query = select(Flow)
        else:
            # Get flows from accessible workspaces
            accessible_workspaces = await workspace_service.get_user_workspaces(
                db=db,
                user_id=current_user.id,
                group_id=current_user.group_id,
                is_admin=current_user.is_superuser
            )
            
            workspace_ids = [ws.id for ws in accessible_workspaces]
            
            if workspace_ids:
                flows_query = select(Flow).join(FlowWorkspaceMap).where(
                    FlowWorkspaceMap.workspace_id.in_(workspace_ids)
                )
            else:
                # No accessible workspaces, return empty list
                return []
    
    result = await db.execute(flows_query)
    flows = result.scalars().all()
    
    # Enhance response with workspace information
    enhanced_flows = []
    for flow in flows:
        # Get workspace info for each flow
        workspace_map_query = select(FlowWorkspaceMap).join(Workspace).where(
            FlowWorkspaceMap.flow_id == flow.id
        )
        workspace_map_result = await db.execute(workspace_map_query)
        workspace_map = workspace_map_result.scalar_one_or_none()
        
        flow_response = FlowResponse.model_validate(flow)
        if workspace_map:
            flow_response.workspace_id = workspace_map.workspace_id
            workspace_result = await db.execute(
                select(Workspace).where(Workspace.id == workspace_map.workspace_id)
            )
            workspace = workspace_result.scalar_one_or_none()
            if workspace:
                flow_response.workspace_name = workspace.name
        
        enhanced_flows.append(flow_response)
    
    return enhanced_flows


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific flow."""
    
    # Get flow
    flow_result = await db.execute(
        select(Flow).where(Flow.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Check workspace access
    workspace_map_result = await db.execute(
        select(FlowWorkspaceMap).where(FlowWorkspaceMap.flow_id == flow_id)
    )
    workspace_map = workspace_map_result.scalar_one_or_none()
    
    if workspace_map:
        # Check if user has access to the workspace
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_map.workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=403, detail="Access denied to this flow")
    elif not current_user.is_superuser and flow.user_id != current_user.id:
        # Flow not in workspace and user doesn't own it
        raise HTTPException(status_code=403, detail="Access denied to this flow")
    
    # Get latest version's definition
    latest_version_result = await db.execute(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
        .limit(1)
    )
    latest_version = latest_version_result.scalar_one_or_none()
    
    # Prepare response with workspace info
    flow_response = FlowResponse.model_validate(flow)
    if workspace_map:
        flow_response.workspace_id = workspace_map.workspace_id
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_map.workspace_id)
        )
        workspace = workspace_result.scalar_one_or_none()
        if workspace:
            flow_response.workspace_name = workspace.name
    
    # Add definition from latest version
    if latest_version:
        flow_response.definition = latest_version.definition
    
    return flow_response


@router.post("/", response_model=FlowResponse)
async def create_flow(
    flow_data: FlowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new flow."""
    
    # Determine workspace
    workspace_id = flow_data.workspace_id
    
    if not workspace_id:
        # Get user's default workspace or first accessible workspace
        accessible_workspaces = await workspace_service.get_user_workspaces(
            db=db,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not accessible_workspaces:
            # Create default workspace if none exists
            default_workspace = await workspace_service.create_default_workspace_for_user(
                db=db,
                user_id=current_user.id,
                username=current_user.username
            )
            workspace_id = default_workspace.id
        else:
            # Use first accessible workspace
            workspace_id = accessible_workspaces[0].id
    else:
        # Verify user has access to specified workspace
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(
                status_code=403,
                detail="Access denied to specified workspace"
            )
    
    # Create flow
    flow_id = str(uuid.uuid4())
    flow = Flow(
        id=flow_id,
        name=flow_data.name,
        description=flow_data.description,
        user_id=current_user.id,
        current_version=1
    )
    db.add(flow)
    await db.flush()
    
    # Add flow to workspace
    flow_workspace_map = FlowWorkspaceMap(
        id=str(uuid.uuid4()),
        flow_id=flow_id,
        workspace_id=workspace_id
    )
    db.add(flow_workspace_map)
    
    # Create initial version if definition provided
    if flow_data.definition:
        version = FlowVersion(
            id=str(uuid.uuid4()),
            flow_id=flow_id,
            version_number=1,
            definition=flow_data.definition,
            change_summary="Initial version",
            created_by=current_user.id
        )
        db.add(version)
    
    await db.commit()
    await db.refresh(flow)
    
    # Add workspace info to response
    flow_response = FlowResponse.model_validate(flow)
    flow_response.workspace_id = workspace_id
    
    # Get workspace name
    workspace_result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        flow_response.workspace_name = workspace.name
    
    return flow_response


@router.put("/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: str,
    flow_data: FlowUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a flow."""
    
    # Get flow
    flow_result = await db.execute(
        select(Flow).where(Flow.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Check workspace access for modification
    workspace_map_result = await db.execute(
        select(FlowWorkspaceMap).where(FlowWorkspaceMap.flow_id == flow_id)
    )
    workspace_map = workspace_map_result.scalar_one_or_none()
    
    if workspace_map:
        # Check if user can modify workspace
        can_modify = await workspace_service.can_modify_workspace(
            db=db,
            workspace_id=workspace_map.workspace_id,
            user_id=current_user.id,
            is_admin=current_user.is_superuser
        )
        
        if not can_modify:
            raise HTTPException(status_code=403, detail="Insufficient permissions to modify this flow")
    elif not current_user.is_superuser and flow.user_id != current_user.id:
        # Flow not in workspace and user doesn't own it
        raise HTTPException(status_code=403, detail="Insufficient permissions to modify this flow")
    
    # Update flow fields
    if flow_data.name is not None:
        flow.name = flow_data.name
    if flow_data.description is not None:
        flow.description = flow_data.description
    
    # Create new version if definition updated
    if flow_data.definition is not None:
        new_version = flow.current_version + 1
        version = FlowVersion(
            id=str(uuid.uuid4()),
            flow_id=flow_id,
            version_number=new_version,
            definition=flow_data.definition,
            change_summary=f"Updated to version {new_version}"
        )
        db.add(version)
        flow.current_version = new_version
    
    await db.commit()
    await db.refresh(flow)
    
    # Prepare response with workspace info
    flow_response = FlowResponse.model_validate(flow)
    if workspace_map:
        flow_response.workspace_id = workspace_map.workspace_id
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_map.workspace_id)
        )
        workspace = workspace_result.scalar_one_or_none()
        if workspace:
            flow_response.workspace_name = workspace.name
    
    return flow_response


@router.delete("/{flow_id}")
async def delete_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a flow."""
    
    # Get flow
    flow_result = await db.execute(
        select(Flow).where(Flow.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Check workspace access for deletion
    workspace_map_result = await db.execute(
        select(FlowWorkspaceMap).where(FlowWorkspaceMap.flow_id == flow_id)
    )
    workspace_map = workspace_map_result.scalar_one_or_none()
    
    if workspace_map:
        # Check if user can modify workspace (needed for deletion)
        can_modify = await workspace_service.can_modify_workspace(
            db=db,
            workspace_id=workspace_map.workspace_id,
            user_id=current_user.id,
            is_admin=current_user.is_superuser
        )
        
        if not can_modify:
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete this flow")
    elif not current_user.is_superuser and flow.user_id != current_user.id:
        # Flow not in workspace and user doesn't own it
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete this flow")
    
    # Delete flow (cascade will handle versions, executions, and workspace mapping)
    await db.execute(delete(Flow).where(Flow.id == flow_id))
    await db.commit()
    
    return {"message": "Flow deleted successfully"}


@router.post("/{flow_id}/save-as", response_model=FlowResponse)
async def save_flow_as(
    flow_id: str,
    save_data: SaveAsFlowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """다른 이름으로 저장 - 기존 Flow를 복제하여 새로운 Flow 생성"""
    
    # 원본 Flow 조회
    original_flow_result = await db.execute(
        select(Flow).where(Flow.id == flow_id)
    )
    original_flow = original_flow_result.scalar_one_or_none()
    
    if not original_flow:
        raise HTTPException(status_code=404, detail="원본 Flow를 찾을 수 없습니다")
    
    # 워크스페이스 접근 권한 확인
    workspace_map_result = await db.execute(
        select(FlowWorkspaceMap).where(FlowWorkspaceMap.flow_id == flow_id)
    )
    workspace_map = workspace_map_result.scalar_one_or_none()
    
    if workspace_map:
        # 워크스페이스에 속한 Flow인 경우 읽기 권한 확인
        workspace = await workspace_service.get_workspace_by_id(
            db=db,
            workspace_id=workspace_map.workspace_id,
            user_id=current_user.id,
            group_id=current_user.group_id,
            is_admin=current_user.is_superuser
        )
        
        if not workspace:
            raise HTTPException(status_code=403, detail="원본 Flow에 접근할 권한이 없습니다")
    elif not current_user.is_superuser and original_flow.user_id != current_user.id:
        # 워크스페이스에 속하지 않은 Flow이고 소유자가 아닌 경우
        raise HTTPException(status_code=403, detail="원본 Flow에 접근할 권한이 없습니다")
    
    # 새 Flow 생성
    new_flow_id = str(uuid.uuid4())
    new_flow = Flow(
        id=new_flow_id,
        name=save_data.name,
        description=save_data.description or f"'{original_flow.name}'에서 복제됨",
        user_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        current_version=1
    )
    
    db.add(new_flow)
    
    # 원본 Flow의 최신 버전 정의 복사
    if original_flow.current_version > 0:
        # 원본의 최신 버전 조회
        latest_version_result = await db.execute(
            select(FlowVersion).where(
                FlowVersion.flow_id == flow_id,
                FlowVersion.version_number == original_flow.current_version
            )
        )
        latest_version = latest_version_result.scalar_one_or_none()
        
        if latest_version and latest_version.definition:
            # 새 Flow의 첫 번째 버전 생성
            new_version = FlowVersion(
                id=str(uuid.uuid4()),
                flow_id=new_flow_id,
                version_number=1,
                definition=latest_version.definition,
                change_summary="Original flow에서 복제됨"
            )
            db.add(new_version)
    
    # 동일한 워크스페이스에 새 Flow 추가 (원본이 워크스페이스에 속한 경우)
    if workspace_map:
        new_workspace_map = FlowWorkspaceMap(
            flow_id=new_flow_id,
            workspace_id=workspace_map.workspace_id,
            created_at=datetime.utcnow()
        )
        db.add(new_workspace_map)
    
    await db.commit()
    await db.refresh(new_flow)
    
    # 응답 준비
    flow_response = FlowResponse.model_validate(new_flow)
    if workspace_map:
        flow_response.workspace_id = workspace_map.workspace_id
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_map.workspace_id)
        )
        workspace = workspace_result.scalar_one_or_none()
        if workspace:
            flow_response.workspace_name = workspace.name
    
    return flow_response