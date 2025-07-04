"""
Group Synchronization Service
Syncs groups from Auth Server to FlowStudio database
"""

import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

import structlog
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.core.database import get_db
from src.models.group import Group

logger = structlog.get_logger(__name__)

AUTH_SERVER_URL = "http://localhost:8000"


class GroupSyncService:
    """Service for syncing groups from Auth Server to local database."""
    
    def __init__(self):
        self.auth_server_url = AUTH_SERVER_URL
    
    async def fetch_groups_from_auth_server(self, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all groups from Auth Server."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.auth_server_url}/admin/groups",
                    headers=headers,
                    params={
                        "limit": 1000,  # Get all groups
                        "is_active": True,
                        "include_system": True
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list):
                    groups = data
                elif isinstance(data, dict) and 'groups' in data:
                    groups = data['groups']
                else:
                    groups = []
                
                logger.info("Fetched groups from Auth Server", count=len(groups))
                return groups
                
        except Exception as e:
            logger.error("Failed to fetch groups from Auth Server", error=str(e))
            raise
    
    async def sync_group_to_database(self, db: AsyncSession, auth_group: Dict[str, Any]) -> Group:
        """Sync a single group from Auth Server to local database."""
        try:
            # Ensure ID is UUID format
            group_id = str(auth_group["id"])
            if not self._is_valid_uuid(group_id):
                raise ValueError(f"Invalid UUID format: {group_id}")
            
            # Check if group already exists
            existing_query = select(Group).where(Group.id == uuid.UUID(group_id))
            result = await db.execute(existing_query)
            existing_group = result.scalar_one_or_none()
            
            group_data = {
                "id": uuid.UUID(group_id),
                "name": auth_group["name"],
                "description": auth_group.get("description"),
                "is_active": auth_group.get("is_active", True),
                "is_system_group": auth_group.get("is_system_group", False),
                "created_by": auth_group.get("created_by"),
                "updated_at": datetime.utcnow()
            }
            
            if existing_group:
                # Update existing group
                for key, value in group_data.items():
                    if key != "id":  # Don't update ID
                        setattr(existing_group, key, value)
                
                logger.debug("Updated existing group", group_id=group_id, name=auth_group["name"])
                return existing_group
            else:
                # Create new group
                group_data["created_at"] = datetime.utcnow()
                new_group = Group(**group_data)
                db.add(new_group)
                
                logger.info("Created new group", group_id=group_id, name=auth_group["name"])
                return new_group
                
        except Exception as e:
            logger.error("Failed to sync group", group_id=auth_group.get("id"), error=str(e))
            raise
    
    async def sync_all_groups(self, preserve_local_groups: bool = True) -> Dict[str, Any]:
        """
        Sync all groups from Auth Server to local database.
        
        Args:
            preserve_local_groups: If True, keep local-only groups. If False, remove them.
        
        Returns:
            Dict with sync statistics
        """
        stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "auth_server_groups": [],
            "local_groups_before": 0,
            "local_groups_after": 0
        }
        
        try:
            # Get database session
            async for db in get_db():
                # Count existing local groups
                local_count_query = select(func.count(Group.id))
                result = await db.execute(local_count_query)
                stats["local_groups_before"] = result.scalar()
                
                # Fetch groups from Auth Server
                auth_groups = await self.fetch_groups_from_auth_server()
                stats["fetched"] = len(auth_groups)
                stats["auth_server_groups"] = [
                    {"id": str(g["id"]), "name": g["name"]} for g in auth_groups
                ]
                
                # Track Auth Server group IDs
                auth_group_ids = set()
                
                # Sync each group
                for auth_group in auth_groups:
                    try:
                        group_id = str(auth_group["id"])
                        auth_group_ids.add(uuid.UUID(group_id))
                        
                        # Check if group exists before sync
                        existing_query = select(Group).where(Group.id == uuid.UUID(group_id))
                        result = await db.execute(existing_query)
                        existed_before = result.scalar_one_or_none() is not None
                        
                        # Sync the group
                        await self.sync_group_to_database(db, auth_group)
                        
                        if existed_before:
                            stats["updated"] += 1
                        else:
                            stats["created"] += 1
                            
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error("Failed to sync individual group", 
                                   group_id=auth_group.get("id"), error=str(e))
                
                # Optionally remove local-only groups (groups not in Auth Server)
                if not preserve_local_groups:
                    local_only_query = select(Group).where(~Group.id.in_(auth_group_ids))
                    result = await db.execute(local_only_query)
                    local_only_groups = result.scalars().all()
                    
                    for group in local_only_groups:
                        if not group.is_system_group:  # Preserve system groups
                            await db.delete(group)
                            logger.info("Removed local-only group", group_id=str(group.id), name=group.name)
                
                # Commit all changes
                await db.commit()
                
                # Count final local groups
                result = await db.execute(local_count_query)
                stats["local_groups_after"] = result.scalar()
                
                logger.info("Group synchronization completed", **stats)
                break  # Exit the async generator loop
                
        except Exception as e:
            logger.error("Group synchronization failed", error=str(e))
            stats["errors"] += 1
            raise
        
        return stats
    
    async def get_group_by_auth_id(self, auth_group_id: str) -> Optional[Group]:
        """Get local group by Auth Server group ID."""
        try:
            if not self._is_valid_uuid(auth_group_id):
                return None
            
            async for db in get_db():
                query = select(Group).where(Group.id == uuid.UUID(auth_group_id))
                result = await db.execute(query)
                group = result.scalar_one_or_none()
                return group
                
        except Exception as e:
            logger.error("Failed to get group by auth ID", auth_group_id=auth_group_id, error=str(e))
            return None
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False


# Global group sync service instance
group_sync_service = GroupSyncService()


# Convenience functions for common operations
async def sync_groups_from_auth_server(preserve_local: bool = True) -> Dict[str, Any]:
    """Sync all groups from Auth Server."""
    return await group_sync_service.sync_all_groups(preserve_local_groups=preserve_local)


async def ensure_group_exists(auth_group_id: str, auth_token: Optional[str] = None) -> Optional[Group]:
    """Ensure a specific group exists locally, fetching from Auth Server if needed."""
    # First check if group already exists locally
    local_group = await group_sync_service.get_group_by_auth_id(auth_group_id)
    if local_group:
        return local_group
    
    # If not found locally, try to fetch and sync from Auth Server
    try:
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            logger.debug(f"Using auth token for group fetch (group_id: {auth_group_id})")
        else:
            logger.warning(f"No auth token provided for group fetch (group_id: {auth_group_id})")
        
        logger.info(f"Fetching group from Auth Server: {AUTH_SERVER_URL}/admin/groups/{auth_group_id}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{AUTH_SERVER_URL}/admin/groups/{auth_group_id}",
                headers=headers
            )
            
            logger.info(f"Auth Server response: {response.status_code}")
            
            if response.status_code == 401:
                logger.error(f"Authentication failed when fetching group {auth_group_id}")
                raise Exception("Authentication failed - invalid or expired token")
            elif response.status_code == 403:
                logger.error(f"Access denied when fetching group {auth_group_id}")
                raise Exception("Access denied - insufficient permissions")
            elif response.status_code == 404:
                logger.error(f"Group {auth_group_id} not found on Auth Server")
                raise Exception(f"Group {auth_group_id} not found on Auth Server")
            
            response.raise_for_status()
            auth_group = response.json()
            
            logger.info(f"Successfully fetched group from Auth Server: {auth_group.get('name', 'Unknown')}")
            
            # Sync this specific group
            async for db in get_db():
                synced_group = await group_sync_service.sync_group_to_database(db, auth_group)
                await db.commit()
                logger.info("Synced single group from Auth Server", 
                          group_id=auth_group_id, 
                          name=auth_group["name"],
                          local_id=str(synced_group.id))
                return synced_group
                
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error when fetching group from Auth Server", 
                   group_id=auth_group_id, 
                   status_code=e.response.status_code,
                   response_text=e.response.text)
        return None
    except httpx.RequestError as e:
        logger.error("Network error when fetching group from Auth Server", 
                   group_id=auth_group_id, 
                   error=str(e))
        return None
    except Exception as e:
        logger.error("Failed to fetch and sync group from Auth Server", 
                   group_id=auth_group_id, 
                   error_type=type(e).__name__,
                   error=str(e))
        return None