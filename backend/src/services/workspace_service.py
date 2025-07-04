"""
Workspace Service - Manages workspace operations and permissions
Flow: Workspace creation -> Permission management -> Access control
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from src.models.workspace import Workspace, WorkspaceType
from src.models.workspace_permission import WorkspacePermission, PermissionType
from src.models.flow_workspace_map import FlowWorkspaceMap
from src.models.user import User
from src.models.flow import Flow

logger = structlog.get_logger(__name__)


class WorkspaceService:
    """Service for managing workspaces and permissions."""
    
    async def create_workspace(
        self,
        db: AsyncSession,
        name: str,
        creator_user_id: str,
        workspace_type: WorkspaceType,
        description: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> Workspace:
        """Create a new workspace."""
        
        workspace_id = str(uuid.uuid4())
        
        workspace = Workspace(
            id=workspace_id,
            name=name,
            description=description,
            type=workspace_type,
            creator_user_id=creator_user_id,
            group_id=group_id if workspace_type == WorkspaceType.GROUP else None,
            is_active=True,
            is_default=False
        )
        
        db.add(workspace)
        await db.flush()  # Get the workspace ID
        
        # Add creator as owner
        permission = WorkspacePermission(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            user_id=creator_user_id,
            permission_type=PermissionType.OWNER
        )
        
        db.add(permission)
        
        # If it's a group workspace, add group permission
        if workspace_type == WorkspaceType.GROUP and group_id:
            group_permission = WorkspacePermission(
                id=str(uuid.uuid4()),
                workspace_id=workspace.id,
                group_id=group_id,
                permission_type=PermissionType.MEMBER
            )
            db.add(group_permission)
        
        await db.commit()
        
        # Refresh workspace with eagerly loaded relationships to prevent lazy loading issues
        workspace_query = select(Workspace).options(
            selectinload(Workspace.permissions),
            selectinload(Workspace.flow_mappings),
            selectinload(Workspace.user_mappings),
            selectinload(Workspace.group_mappings)
        ).where(Workspace.id == workspace.id)
        result = await db.execute(workspace_query)
        workspace = result.scalar_one()
        
        logger.info(
            "Workspace created",
            workspace_id=workspace.id,
            name=name,
            type=workspace_type,
            creator_user_id=creator_user_id
        )
        
        return workspace
    
    async def get_user_workspaces(
        self,
        db: AsyncSession,
        user_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Workspace]:
        """Get workspaces accessible to a user."""
        
        if is_admin:
            # Admin can see all workspaces
            query = select(Workspace).options(
                selectinload(Workspace.permissions),
                selectinload(Workspace.flow_mappings)
            ).where(Workspace.is_active == True)
        else:
            # Build conditions for user access
            conditions = [
                # User has direct permission
                and_(
                    WorkspacePermission.user_id == user_id,
                    WorkspacePermission.workspace_id == Workspace.id
                )
            ]
            
            # Add group permission if user has group_id
            if group_id:
                conditions.append(
                    and_(
                        WorkspacePermission.group_id == group_id,
                        WorkspacePermission.workspace_id == Workspace.id
                    )
                )
            
            query = select(Workspace).options(
                selectinload(Workspace.permissions),
                selectinload(Workspace.flow_mappings)
            ).join(WorkspacePermission).where(
                and_(
                    Workspace.is_active == True,
                    or_(*conditions)
                )
            ).distinct()
        
        result = await db.execute(query)
        workspaces = result.scalars().unique().all()
        
        return list(workspaces)
    
    async def get_workspace_by_id(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Optional[Workspace]:
        """Get workspace by ID if user has access."""
        
        if is_admin:
            # Admin can access any workspace
            query = select(Workspace).options(
                selectinload(Workspace.permissions),
                selectinload(Workspace.flow_mappings)
            ).where(
                and_(
                    Workspace.id == workspace_id,
                    Workspace.is_active == True
                )
            )
        else:
            # Check user permissions
            conditions = [
                WorkspacePermission.user_id == user_id
            ]
            
            if group_id:
                conditions.append(WorkspacePermission.group_id == group_id)
            
            query = select(Workspace).options(
                selectinload(Workspace.permissions),
                selectinload(Workspace.flow_mappings)
            ).join(WorkspacePermission).where(
                and_(
                    Workspace.id == workspace_id,
                    Workspace.is_active == True,
                    or_(*conditions)
                )
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Optional[Workspace]:
        """Update workspace if user has permission."""
        
        # Check if user can modify workspace
        if not await self.can_modify_workspace(db, workspace_id, user_id, is_admin):
            return None
        
        query = select(Workspace).where(Workspace.id == workspace_id)
        result = await db.execute(query)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return None
        
        # Update fields
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        
        workspace.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Refresh workspace with eagerly loaded relationships to prevent lazy loading issues
        workspace_query = select(Workspace).options(
            selectinload(Workspace.permissions),
            selectinload(Workspace.flow_mappings),
            selectinload(Workspace.user_mappings),
            selectinload(Workspace.group_mappings)
        ).where(Workspace.id == workspace_id)
        result = await db.execute(workspace_query)
        workspace = result.scalar_one()
        
        return workspace
    
    async def delete_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """Delete workspace if user has permission."""
        
        # Check if user can delete workspace (must be owner or admin)
        if not await self.can_delete_workspace(db, workspace_id, user_id, is_admin):
            return False
        
        query = select(Workspace).where(Workspace.id == workspace_id)
        result = await db.execute(query)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return False
        
        # Soft delete
        workspace.is_active = False
        workspace.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(
            "Workspace deleted",
            workspace_id=workspace_id,
            user_id=user_id
        )
        
        return True
    
    async def add_flow_to_workspace(
        self,
        db: AsyncSession,
        flow_id: str,
        workspace_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """Add flow to workspace."""
        
        # Check if user can modify workspace
        if not await self.can_modify_workspace(db, workspace_id, user_id, is_admin):
            return False
        
        # Check if flow exists and user owns it (or is admin)
        flow_query = select(Flow).where(Flow.id == flow_id)
        if not is_admin:
            flow_query = flow_query.where(Flow.user_id == user_id)
        
        result = await db.execute(flow_query)
        flow = result.scalar_one_or_none()
        
        if not flow:
            return False
        
        # Check if flow is already in a workspace
        existing_map_query = select(FlowWorkspaceMap).where(
            FlowWorkspaceMap.flow_id == flow_id
        )
        result = await db.execute(existing_map_query)
        existing_map = result.scalar_one_or_none()
        
        if existing_map:
            # Update existing mapping
            existing_map.workspace_id = workspace_id
            existing_map.updated_at = datetime.utcnow()
        else:
            # Create new mapping
            flow_map = FlowWorkspaceMap(
                id=str(uuid.uuid4()),
                flow_id=flow_id,
                workspace_id=workspace_id
            )
            db.add(flow_map)
        
        await db.commit()
        return True
    
    async def get_user_permission(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        group_id: Optional[str] = None
    ) -> Optional[PermissionType]:
        """Get user's permission level for a workspace."""
        
        # Check direct user permission first
        user_perm_query = select(WorkspacePermission).where(
            and_(
                WorkspacePermission.workspace_id == workspace_id,
                WorkspacePermission.user_id == user_id
            )
        )
        result = await db.execute(user_perm_query)
        user_permission = result.scalar_one_or_none()
        
        if user_permission:
            return user_permission.permission_type
        
        # Check group permission
        if group_id:
            group_perm_query = select(WorkspacePermission).where(
                and_(
                    WorkspacePermission.workspace_id == workspace_id,
                    WorkspacePermission.group_id == group_id
                )
            )
            result = await db.execute(group_perm_query)
            group_permission = result.scalar_one_or_none()
            
            if group_permission:
                return group_permission.permission_type
        
        return None
    
    async def can_modify_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """Check if user can modify workspace."""
        
        if is_admin:
            return True
        
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        permission = await self.get_user_permission(
            db, workspace_id, user_id, user.group_id
        )
        
        return permission in [PermissionType.OWNER, PermissionType.ADMIN]
    
    async def can_delete_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """Check if user can delete workspace."""
        
        if is_admin:
            return True
        
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        permission = await self.get_user_permission(
            db, workspace_id, user_id, user.group_id
        )
        
        return permission == PermissionType.OWNER
    
    async def create_default_workspace_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        username: str
    ) -> Workspace:
        """Create default personal workspace for new user."""
        
        workspace_name = f"{username}'s Workspace"
        
        return await self.create_workspace(
            db=db,
            name=workspace_name,
            creator_user_id=user_id,
            workspace_type=WorkspaceType.USER,
            description="Default personal workspace"
        )


    async def get_user_accessible_workspaces_with_mappings(
        self,
        db: AsyncSession,
        user_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Workspace]:
        """
        사용자가 접근할 수 있는 워크스페이스 조회 (새로운 매핑 시스템 사용)
        
        우선순위:
        1. 직접 사용자 매핑 (WorkspaceUserMapping)
        2. 그룹 매핑 (WorkspaceGroupMapping)
        3. 기존 권한 시스템 (WorkspacePermission)
        4. 관리자는 모든 워크스페이스 접근 가능
        """
        from src.models.workspace_mapping import WorkspaceUserMapping, WorkspaceGroupMapping
        
        if is_admin:
            # 관리자는 모든 활성 워크스페이스에 접근 가능
            query = select(Workspace).options(
                selectinload(Workspace.flow_mappings),
                selectinload(Workspace.permissions)
            ).where(Workspace.is_active == True).order_by(Workspace.name)
            
            result = await db.execute(query)
            return result.scalars().all()
        
        # 접근 가능한 워크스페이스 ID 수집
        accessible_workspace_ids = set()
        
        # 1. 직접 사용자 매핑을 통한 접근
        user_mapping_query = select(WorkspaceUserMapping.workspace_id).where(
            WorkspaceUserMapping.user_id == user_id
        )
        user_mapping_result = await db.execute(user_mapping_query)
        user_mapped_workspace_ids = user_mapping_result.scalars().all()
        accessible_workspace_ids.update(user_mapped_workspace_ids)
        
        # 2. 그룹 매핑을 통한 접근 (사용자가 그룹에 속한 경우)
        if group_id:
            try:
                group_uuid = uuid.UUID(group_id)
                group_mapping_query = select(WorkspaceGroupMapping.workspace_id).where(
                    WorkspaceGroupMapping.group_id == group_uuid
                )
                group_mapping_result = await db.execute(group_mapping_query)
                group_mapped_workspace_ids = group_mapping_result.scalars().all()
                accessible_workspace_ids.update(group_mapped_workspace_ids)
            except ValueError:
                # group_id가 유효한 UUID가 아닌 경우 기존 방식으로 처리
                pass
        
        # 3. 기존 권한 시스템을 통한 접근 (기존 사용자와의 호환성)
        legacy_permission_query = select(WorkspacePermission.workspace_id).where(
            or_(
                WorkspacePermission.user_id == user_id,
                and_(
                    WorkspacePermission.group_id == group_id,
                    group_id.is_not(None)
                ) if group_id else False
            )
        )
        legacy_permission_result = await db.execute(legacy_permission_query)
        legacy_workspace_ids = legacy_permission_result.scalars().all()
        accessible_workspace_ids.update(legacy_workspace_ids)
        
        # 4. 워크스페이스 생성자인 경우 (항상 접근 가능)
        creator_query = select(Workspace.id).where(
            and_(
                Workspace.creator_user_id == user_id,
                Workspace.is_active == True
            )
        )
        creator_result = await db.execute(creator_query)
        creator_workspace_ids = creator_result.scalars().all()
        accessible_workspace_ids.update(creator_workspace_ids)
        
        if not accessible_workspace_ids:
            return []
        
        # 최종 워크스페이스 조회
        workspaces_query = select(Workspace).options(
            selectinload(Workspace.flow_mappings),
            selectinload(Workspace.permissions),
            selectinload(Workspace.user_mappings),
            selectinload(Workspace.group_mappings)
        ).where(
            and_(
                Workspace.id.in_(accessible_workspace_ids),
                Workspace.is_active == True
            )
        ).order_by(Workspace.name)
        
        result = await db.execute(workspaces_query)
        return result.scalars().all()
    
    async def get_user_permission_with_mappings(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        group_id: Optional[str] = None
    ) -> Optional[PermissionType]:
        """
        새로운 매핑 시스템을 사용한 사용자 권한 조회
        
        우선순위:
        1. 직접 사용자 매핑 (WorkspaceUserMapping)
        2. 그룹 매핑 (WorkspaceGroupMapping)  
        3. 기존 권한 시스템 (WorkspacePermission)
        4. 워크스페이스 생성자 권한
        """
        from src.models.workspace_mapping import (
            WorkspaceUserMapping, 
            WorkspaceGroupMapping, 
            WorkspacePermissionLevel
        )
        
        # 1. 직접 사용자 매핑 확인
        user_mapping_query = select(WorkspaceUserMapping).where(
            and_(
                WorkspaceUserMapping.workspace_id == workspace_id,
                WorkspaceUserMapping.user_id == user_id
            )
        )
        user_mapping_result = await db.execute(user_mapping_query)
        user_mapping = user_mapping_result.scalar_one_or_none()
        
        if user_mapping:
            # 새로운 권한 레벨을 기존 PermissionType으로 변환
            return self._convert_permission_level_to_type(user_mapping.permission_level)
        
        # 2. 그룹 매핑 확인
        if group_id:
            try:
                group_uuid = uuid.UUID(group_id)
                group_mapping_query = select(WorkspaceGroupMapping).where(
                    and_(
                        WorkspaceGroupMapping.workspace_id == workspace_id,
                        WorkspaceGroupMapping.group_id == group_uuid
                    )
                )
                group_mapping_result = await db.execute(group_mapping_query)
                group_mapping = group_mapping_result.scalar_one_or_none()
                
                if group_mapping:
                    return self._convert_permission_level_to_type(group_mapping.permission_level)
            except ValueError:
                pass
        
        # 3. 기존 권한 시스템 확인 (하위 호환성)
        permission_query = select(WorkspacePermission).where(
            and_(
                WorkspacePermission.workspace_id == workspace_id,
                or_(
                    WorkspacePermission.user_id == user_id,
                    and_(
                        WorkspacePermission.group_id == group_id,
                        group_id.is_not(None)
                    ) if group_id else False
                )
            )
        )
        permission_result = await db.execute(permission_query)
        permission = permission_result.scalar_one_or_none()
        
        if permission:
            return permission.permission_type
        
        # 4. 워크스페이스 생성자 권한 확인
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        if workspace and workspace.creator_user_id == user_id:
            return PermissionType.OWNER
        
        return None
    
    def _convert_permission_level_to_type(self, permission_level) -> PermissionType:
        """새로운 WorkspacePermissionLevel을 기존 PermissionType으로 변환"""
        from src.models.workspace_mapping import WorkspacePermissionLevel
        
        mapping = {
            WorkspacePermissionLevel.OWNER: PermissionType.OWNER,
            WorkspacePermissionLevel.ADMIN: PermissionType.ADMIN,
            WorkspacePermissionLevel.MEMBER: PermissionType.MEMBER,
            WorkspacePermissionLevel.VIEWER: PermissionType.VIEWER,
        }
        return mapping.get(permission_level, PermissionType.VIEWER)


# Global workspace service instance
workspace_service = WorkspaceService()