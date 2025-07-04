"""
Flow Version API endpoints
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.core.auth import get_current_user
from src.services.flow_version_service import flow_version_service
from src.core.exceptions import NotFoundError, ValidationError
from src.models.user import User

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/flows", tags=["flow-versions"])


class CreateVersionRequest(BaseModel):
    """Request model for creating a new version"""
    definition: dict = Field(..., description="Flow definition (nodes, edges, etc.)")
    version_name: Optional[str] = Field(None, max_length=255, description="Optional custom name for the version")
    description: Optional[str] = Field(None, description="Description of changes in this version")
    change_summary: Optional[str] = Field(None, description="Summary of changes made")


class PublishVersionRequest(BaseModel):
    """Request model for publishing a version"""
    version_id: str = Field(..., description="ID of the version to publish")


class RestoreVersionRequest(BaseModel):
    """Request model for restoring a version"""
    create_new_version: bool = Field(True, description="Whether to create a new version when restoring")


class FlowVersionResponse(BaseModel):
    """Response model for flow version"""
    id: str
    flow_id: str
    version_number: int
    version_name: Optional[str]
    description: Optional[str]
    definition: dict
    is_published: bool
    published_at: Optional[str]
    published_by: Optional[str]
    change_summary: Optional[str]
    parent_version_id: Optional[str]
    created_at: str
    created_by: str
    display_name: str

    model_config = {"from_attributes": True}


@router.post("/{flow_id}/versions", response_model=FlowVersionResponse)
async def create_version(
    flow_id: str,
    request: CreateVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of a flow"""
    try:
        # Get the latest version to use as parent
        latest_version = await flow_version_service.get_latest_version(db, flow_id)
        parent_version_id = latest_version.id if latest_version else None
        
        version = await flow_version_service.create_version(
            db=db,
            flow_id=flow_id,
            definition=request.definition,
            created_by=current_user.id,
            version_name=request.version_name,
            description=request.description,
            change_summary=request.change_summary,
            parent_version_id=parent_version_id
        )
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{flow_id}/versions", response_model=List[FlowVersionResponse])
async def get_versions(
    flow_id: str,
    include_unpublished: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all versions of a flow"""
    try:
        versions = await flow_version_service.get_versions(
            db=db,
            flow_id=flow_id,
            include_unpublished=include_unpublished
        )
        
        return [
            FlowVersionResponse(
                id=version.id,
                flow_id=version.flow_id,
                version_number=version.version_number,
                version_name=version.version_name,
                description=version.description,
                definition=version.definition,
                is_published=version.is_published,
                published_at=version.published_at.isoformat() if version.published_at else None,
                published_by=version.published_by,
                change_summary=version.change_summary,
                parent_version_id=version.parent_version_id,
                created_at=version.created_at.isoformat(),
                created_by=version.created_by,
                display_name=version.display_name
            )
            for version in versions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{flow_id}/versions/{version_number}", response_model=FlowVersionResponse)
async def get_version_by_number(
    flow_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific version by version number"""
    try:
        version = await flow_version_service.get_version_by_number(
            db=db,
            flow_id=flow_id,
            version_number=version_number
        )
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_number} not found for flow {flow_id}"
            )
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{flow_id}/versions/{version_id}/publish", response_model=FlowVersionResponse)
async def publish_version(
    flow_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish a version"""
    logger.info(f"Publishing version {version_id} for flow {flow_id} by user {current_user.id}")
    
    try:
        # Validate inputs
        if not flow_id or not version_id:
            logger.error(f"Invalid input - flow_id: {flow_id}, version_id: {version_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Flow ID and Version ID are required")
            
        if not current_user or not current_user.id:
            logger.error("Current user ID is missing")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User authentication required")
        
        version = await flow_version_service.publish_version(
            db=db,
            version_id=version_id,
            published_by=current_user.id
        )
        
        logger.info(f"Successfully published version {version_id} for flow {flow_id}")
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except NotFoundError as e:
        logger.error(f"Version not found for publishing - flow_id: {flow_id}, version_id: {version_id}, error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        logger.error(f"Validation error during publishing - flow_id: {flow_id}, version_id: {version_id}, error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during publishing - flow_id: {flow_id}, version_id: {version_id}, error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")


@router.post("/{flow_id}/versions/{version_id}/unpublish", response_model=FlowVersionResponse)
async def unpublish_version(
    flow_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unpublish a version"""
    try:
        version = await flow_version_service.unpublish_version(
            db=db,
            version_id=version_id
        )
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{flow_id}/versions/{version_id}/restore", response_model=FlowVersionResponse)
async def restore_version(
    flow_id: str,
    version_id: str,
    request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore a previous version"""
    try:
        version = await flow_version_service.restore_version(
            db=db,
            version_id=version_id,
            restored_by=current_user.id,
            create_new_version=request.create_new_version
        )
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{flow_id}/versions/published", response_model=FlowVersionResponse)
async def get_published_version(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the currently published version of a flow"""
    try:
        version = await flow_version_service.get_published_version(db=db, flow_id=flow_id)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No published version found for flow {flow_id}"
            )
        
        return FlowVersionResponse(
            id=version.id,
            flow_id=version.flow_id,
            version_number=version.version_number,
            version_name=version.version_name,
            description=version.description,
            definition=version.definition,
            is_published=version.is_published,
            published_at=version.published_at.isoformat() if version.published_at else None,
            published_by=version.published_by,
            change_summary=version.change_summary,
            parent_version_id=version.parent_version_id,
            created_at=version.created_at.isoformat(),
            created_by=version.created_by,
            display_name=version.display_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{flow_id}/versions/{version_id}")
async def delete_version(
    flow_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a version (if not published and not the only version)"""
    try:
        success = await flow_version_service.delete_version(db=db, version_id=version_id)
        
        if success:
            return {"message": "Version deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete version"
            )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))