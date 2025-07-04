"""
Role-Based Access Control (RBAC) Middleware
Flow: Request -> Auth -> Permission Check -> Resource Access
"""

from typing import Optional, List
from functools import wraps

from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User
from src.models.workspace import Workspace
from src.models.workspace_permission import WorkspacePermission, PermissionType
from src.middleware.auth import get_current_user
from src.core.database import AsyncSessionLocal


class RBACError(Exception):
    """RBAC-specific exception."""
    pass


class PermissionChecker:
    """Utility class for checking permissions."""
    
    @staticmethod
    async def has_workspace_permission(
        user_id: str,
        workspace_id: str,
        required_permissions: List[PermissionType],
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """Check if user has required permission for workspace."""
        
        if is_admin:
            return True
        
        async with AsyncSessionLocal() as db:
            # Check direct user permission
            user_perm_query = select(WorkspacePermission).where(
                WorkspacePermission.workspace_id == workspace_id,
                WorkspacePermission.user_id == user_id
            )
            result = await db.execute(user_perm_query)
            user_permission = result.scalar_one_or_none()
            
            if user_permission and user_permission.permission_type in required_permissions:
                return True
            
            # Check group permission if available
            if group_id:
                group_perm_query = select(WorkspacePermission).where(
                    WorkspacePermission.workspace_id == workspace_id,
                    WorkspacePermission.group_id == group_id
                )
                result = await db.execute(group_perm_query)
                group_permission = result.scalar_one_or_none()
                
                if group_permission and group_permission.permission_type in required_permissions:
                    return True
        
        return False
    
    @staticmethod
    async def can_access_workspace(
        user_id: str,
        workspace_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """Check if user can access workspace (any permission level)."""
        
        return await PermissionChecker.has_workspace_permission(
            user_id=user_id,
            workspace_id=workspace_id,
            required_permissions=[
                PermissionType.OWNER,
                PermissionType.ADMIN,
                PermissionType.MEMBER,
                PermissionType.VIEWER
            ],
            group_id=group_id,
            is_admin=is_admin
        )
    
    @staticmethod
    async def can_modify_workspace(
        user_id: str,
        workspace_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """Check if user can modify workspace (admin/owner permissions)."""
        
        return await PermissionChecker.has_workspace_permission(
            user_id=user_id,
            workspace_id=workspace_id,
            required_permissions=[
                PermissionType.OWNER,
                PermissionType.ADMIN
            ],
            group_id=group_id,
            is_admin=is_admin
        )
    
    @staticmethod
    async def can_delete_workspace(
        user_id: str,
        workspace_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """Check if user can delete workspace (owner permission only)."""
        
        return await PermissionChecker.has_workspace_permission(
            user_id=user_id,
            workspace_id=workspace_id,
            required_permissions=[PermissionType.OWNER],
            group_id=group_id,
            is_admin=is_admin
        )
    
    @staticmethod
    async def can_manage_flows(
        user_id: str,
        workspace_id: str,
        group_id: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """Check if user can create/edit flows in workspace."""
        
        return await PermissionChecker.has_workspace_permission(
            user_id=user_id,
            workspace_id=workspace_id,
            required_permissions=[
                PermissionType.OWNER,
                PermissionType.ADMIN,
                PermissionType.MEMBER
            ],
            group_id=group_id,
            is_admin=is_admin
        )


def require_permission(required_permissions: List[PermissionType]):
    """Decorator to require specific permissions for workspace access."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and workspace_id from function arguments
            request = None
            workspace_id = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            workspace_id = kwargs.get('workspace_id')
            
            if not request or not workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing request or workspace_id for permission check"
                )
            
            # Get current user
            current_user = get_current_user(request)
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get user from database to get group_id
            async with AsyncSessionLocal() as db:
                user_result = await db.execute(
                    select(User).where(User.id == current_user["id"])
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found"
                    )
            
            # Check permissions
            has_permission = await PermissionChecker.has_workspace_permission(
                user_id=user.id,
                workspace_id=workspace_id,
                required_permissions=required_permissions,
                group_id=user.group_id,
                is_admin=user.is_superuser
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for this operation"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_workspace_access():
    """Decorator to require any level of workspace access."""
    return require_permission([
        PermissionType.OWNER,
        PermissionType.ADMIN,
        PermissionType.MEMBER,
        PermissionType.VIEWER
    ])


def require_workspace_modify():
    """Decorator to require workspace modification permissions."""
    return require_permission([
        PermissionType.OWNER,
        PermissionType.ADMIN
    ])


def require_workspace_owner():
    """Decorator to require workspace owner permissions."""
    return require_permission([PermissionType.OWNER])


def require_admin():
    """Decorator to require admin (superuser) permissions."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing request for admin check"
                )
            
            current_user = get_current_user(request)
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not current_user.get("is_superuser", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin privileges required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global permission checker instance
permission_checker = PermissionChecker()