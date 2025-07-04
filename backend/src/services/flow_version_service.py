"""
Flow Version Service
Handles version management for flows
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from src.models.flow import Flow, FlowVersion
from src.core.exceptions import NotFoundError, ValidationError


class FlowVersionService:
    """Service for managing flow versions"""

    async def create_version(
        self,
        db: AsyncSession,
        flow_id: str,
        definition: Dict[str, Any],
        created_by: str,
        version_name: Optional[str] = None,
        description: Optional[str] = None,
        change_summary: Optional[str] = None,
        parent_version_id: Optional[str] = None
    ) -> FlowVersion:
        """Create a new version of a flow"""
        
        # Get the flow
        flow_result = await db.execute(
            select(Flow).where(Flow.id == flow_id)
        )
        flow = flow_result.scalar_one_or_none()
        if not flow:
            raise NotFoundError(f"Flow with id {flow_id} not found")
        
        # Get the next version number
        latest_version_result = await db.execute(
            select(FlowVersion)
            .where(FlowVersion.flow_id == flow_id)
            .order_by(desc(FlowVersion.version_number))
            .limit(1)
        )
        latest_version = latest_version_result.scalar_one_or_none()
        next_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create new version
        new_version = FlowVersion(
            id=str(uuid.uuid4()),
            flow_id=flow_id,
            version_number=next_version_number,
            version_name=version_name,
            description=description,
            definition=definition,
            change_summary=change_summary,
            parent_version_id=parent_version_id,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        db.add(new_version)
        
        # Update flow's current version
        flow.current_version = next_version_number
        flow.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(new_version)
        
        return new_version

    async def get_versions(
        self,
        db: AsyncSession,
        flow_id: str,
        include_unpublished: bool = True
    ) -> List[FlowVersion]:
        """Get all versions of a flow"""
        
        query = select(FlowVersion).where(FlowVersion.flow_id == flow_id)
        
        if not include_unpublished:
            query = query.where(FlowVersion.is_published == True)
        
        query = query.order_by(desc(FlowVersion.version_number))
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_version(
        self,
        db: AsyncSession,
        version_id: str
    ) -> Optional[FlowVersion]:
        """Get a specific version by ID"""
        
        result = await db.execute(
            select(FlowVersion)
            .options(selectinload(FlowVersion.flow))
            .where(FlowVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_version_by_number(
        self,
        db: AsyncSession,
        flow_id: str,
        version_number: int
    ) -> Optional[FlowVersion]:
        """Get a specific version by flow ID and version number"""
        
        result = await db.execute(
            select(FlowVersion)
            .options(selectinload(FlowVersion.flow))
            .where(
                and_(
                    FlowVersion.flow_id == flow_id,
                    FlowVersion.version_number == version_number
                )
            )
        )
        return result.scalar_one_or_none()

    async def publish_version(
        self,
        db: AsyncSession,
        version_id: str,
        published_by: str
    ) -> FlowVersion:
        """Publish a version"""
        
        version = await self.get_version(db, version_id)
        if not version:
            raise NotFoundError(f"Version with id {version_id} not found")
        
        # Unpublish any currently published version of this flow
        current_published_result = await db.execute(
            select(FlowVersion)
            .where(
                and_(
                    FlowVersion.flow_id == version.flow_id,
                    FlowVersion.is_published == True
                )
            )
        )
        current_published = current_published_result.scalars().all()
        
        for published_version in current_published:
            published_version.is_published = False
            published_version.published_at = None
            published_version.published_by = None
        
        # Publish the new version
        version.is_published = True
        version.published_at = datetime.utcnow()
        version.published_by = published_by
        
        await db.commit()
        await db.refresh(version)
        
        return version

    async def unpublish_version(
        self,
        db: AsyncSession,
        version_id: str
    ) -> FlowVersion:
        """Unpublish a version"""
        
        version = await self.get_version(db, version_id)
        if not version:
            raise NotFoundError(f"Version with id {version_id} not found")
        
        version.is_published = False
        version.published_at = None
        version.published_by = None
        
        await db.commit()
        await db.refresh(version)
        
        return version

    async def restore_version(
        self,
        db: AsyncSession,
        version_id: str,
        restored_by: str,
        create_new_version: bool = True
    ) -> FlowVersion:
        """Restore a previous version"""
        
        old_version = await self.get_version(db, version_id)
        if not old_version:
            raise NotFoundError(f"Version with id {version_id} not found")
        
        if create_new_version:
            # Create a new version based on the old one
            new_version = await self.create_version(
                db=db,
                flow_id=old_version.flow_id,
                definition=old_version.definition,
                created_by=restored_by,
                version_name=f"Restored from v{old_version.version_number}",
                description=f"Restored from version {old_version.version_number}",
                change_summary=f"Restored from version {old_version.version_number}",
                parent_version_id=old_version.id
            )
            return new_version
        else:
            # Update flow to point to the old version
            flow_result = await db.execute(
                select(Flow).where(Flow.id == old_version.flow_id)
            )
            flow = flow_result.scalar_one_or_none()
            if flow:
                flow.current_version = old_version.version_number
                flow.updated_at = datetime.utcnow()
                await db.commit()
            
            return old_version

    async def get_published_version(
        self,
        db: AsyncSession,
        flow_id: str
    ) -> Optional[FlowVersion]:
        """Get the currently published version of a flow"""
        
        result = await db.execute(
            select(FlowVersion)
            .where(
                and_(
                    FlowVersion.flow_id == flow_id,
                    FlowVersion.is_published == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(
        self,
        db: AsyncSession,
        flow_id: str
    ) -> Optional[FlowVersion]:
        """Get the latest version of a flow"""
        
        result = await db.execute(
            select(FlowVersion)
            .where(FlowVersion.flow_id == flow_id)
            .order_by(desc(FlowVersion.version_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_version(
        self,
        db: AsyncSession,
        version_id: str
    ) -> bool:
        """Delete a version (if not published and not the only version)"""
        
        version = await self.get_version(db, version_id)
        if not version:
            raise NotFoundError(f"Version with id {version_id} not found")
        
        if version.is_published:
            raise ValidationError("Cannot delete a published version")
        
        # Check if this is the only version
        versions_count_result = await db.execute(
            select(FlowVersion)
            .where(FlowVersion.flow_id == version.flow_id)
        )
        versions_count = len(versions_count_result.scalars().all())
        
        if versions_count <= 1:
            raise ValidationError("Cannot delete the only version of a flow")
        
        await db.delete(version)
        await db.commit()
        
        return True


# Global instance
flow_version_service = FlowVersionService()