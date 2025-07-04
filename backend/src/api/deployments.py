"""
API Deployment endpoints
Flow: Create deployment -> Generate API endpoint -> Manage deployment lifecycle
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.api_deployment import ApiDeployment, DeploymentStatus
from src.models.flow import Flow
from src.models.user import User
from src.services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


class CreateDeploymentRequest(BaseModel):
    """Request to create a new API deployment."""
    flow_id: str
    name: str
    description: Optional[str] = None
    endpoint_path: str = Field(..., pattern=r"^/[a-zA-Z0-9\-_/]+$")
    is_public: bool = False
    requires_auth: bool = True
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    deployment_config: Optional[Dict[str, Any]] = None


class UpdateDeploymentRequest(BaseModel):
    """Request to update an existing deployment."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    requires_auth: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    deployment_config: Optional[Dict[str, Any]] = None


class DeploymentResponse(BaseModel):
    """API deployment response model."""
    id: str
    flow_id: str
    name: str
    description: Optional[str]
    endpoint_path: str
    version: str
    status: DeploymentStatus
    is_public: bool
    requires_auth: bool
    rate_limit: Optional[int]
    total_requests: int
    last_request_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime]
    error_message: Optional[str]
    
    model_config = {"from_attributes": True}


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    request: CreateDeploymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """Create a new API deployment."""
    
    # Verify flow exists and user owns it
    flow_query = select(Flow).where(
        Flow.id == request.flow_id,
        Flow.user_id == current_user.id
    )
    result = await db.execute(flow_query)
    flow = result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found or access denied"
        )
    
    # Check if endpoint path is already taken
    existing_query = select(ApiDeployment).where(
        ApiDeployment.endpoint_path == request.endpoint_path
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Endpoint path already exists"
        )
    
    # Create deployment
    deployment = ApiDeployment(
        id=str(uuid.uuid4()),
        flow_id=request.flow_id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        endpoint_path=request.endpoint_path,
        is_public=request.is_public,
        requires_auth=request.requires_auth,
        rate_limit=request.rate_limit,
        input_schema=request.input_schema,
        output_schema=request.output_schema,
        deployment_config=request.deployment_config,
        status=DeploymentStatus.PENDING
    )
    
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    
    # For 2-stage approval process, don't auto-deploy
    # Deployment will be activated when admin approves it
    logger.info(
        "Deployment created in pending status",
        deployment_id=deployment.id,
        endpoint_path=deployment.endpoint_path,
        status=deployment.status
    )
    
    return DeploymentResponse.model_validate(deployment)


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    flow_id: Optional[str] = None,
    include_all: bool = False,
    include_flows: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DeploymentResponse]:
    """List deployments for the current user or all deployments for admin."""
    
    query = select(ApiDeployment)
    
    # Admin users can see all deployments if include_all=True
    if current_user.is_superuser and include_all:
        # No user filter for admin - show all deployments
        pass
    else:
        # Regular users or admin without include_all flag
        query = query.where(ApiDeployment.user_id == current_user.id)
    
    # Filter by flow_id if provided
    if flow_id:
        query = query.where(ApiDeployment.flow_id == flow_id)
    
    query = query.order_by(ApiDeployment.created_at.desc())
    result = await db.execute(query)
    deployments = result.scalars().all()
    
    return [DeploymentResponse.model_validate(d) for d in deployments]


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """Get a specific deployment."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    return DeploymentResponse.model_validate(deployment)


@router.put("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: str,
    request: UpdateDeploymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """Update an existing deployment."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deployment, field, value)
    
    # If deployment_config is updated (indicating new flow version deployment),
    # update deployed_at timestamp and set status to active
    if 'deployment_config' in update_data:
        deployment.deployed_at = datetime.utcnow()
        deployment.status = DeploymentStatus.ACTIVE
    
    deployment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(deployment)
    
    return DeploymentResponse.model_validate(deployment)


@router.post("/{deployment_id}/activate")
async def activate_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Activate a deployment."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    if deployment.status == DeploymentStatus.ACTIVE:
        return {"message": "Deployment already active"}
    
    # Activate deployment
    deployment_service = DeploymentService()
    try:
        await deployment_service.activate_deployment(deployment_id, db)
        return {"message": "Deployment activated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate deployment: {str(e)}"
        )


@router.put("/{deployment_id}/status")
async def update_deployment_status(
    deployment_id: str,
    status_update: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """Update deployment status (for admin approval/rejection)."""
    
    # Admin can update any deployment, regular users only their own
    query = select(ApiDeployment).where(ApiDeployment.id == deployment_id)
    if not current_user.is_superuser:
        query = query.where(ApiDeployment.user_id == current_user.id)
    
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    new_status = status_update.get("status")
    if not new_status or new_status not in ["active", "inactive", "pending", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )
    
    # Handle status transitions
    deployment_service = DeploymentService()
    
    try:
        if new_status == "active" and deployment.status != DeploymentStatus.ACTIVE:
            # Activate deployment (deploy API endpoint)
            await deployment_service.deploy_api(deployment_id, db)
        elif new_status == "inactive" and deployment.status == DeploymentStatus.ACTIVE:
            # Deactivate deployment
            await deployment_service.deactivate_deployment(deployment_id, db)
        else:
            # Just update status
            deployment.status = DeploymentStatus(new_status)
            deployment.updated_at = datetime.utcnow()
            await db.commit()
        
        await db.refresh(deployment)
        return DeploymentResponse.model_validate(deployment)
        
    except Exception as e:
        logger.error(f"Failed to update deployment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deployment status: {str(e)}"
        )


@router.post("/{deployment_id}/deactivate")
async def deactivate_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Deactivate a deployment."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    if deployment.status == DeploymentStatus.INACTIVE:
        return {"message": "Deployment already inactive"}
    
    # Deactivate deployment
    deployment_service = DeploymentService()
    try:
        await deployment_service.deactivate_deployment(deployment_id, db)
        return {"message": "Deployment deactivated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate deployment: {str(e)}"
        )


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete a deployment."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Delete deployment
    deployment_service = DeploymentService()
    try:
        await deployment_service.delete_deployment(deployment_id, db)
        return {"message": "Deployment deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployment: {str(e)}"
        )


@router.get("/{deployment_id}/stats")
async def get_deployment_stats(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get deployment usage statistics."""
    
    query = select(ApiDeployment).where(
        ApiDeployment.id == deployment_id,
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    return {
        "deployment_id": deployment.id,
        "name": deployment.name,
        "status": deployment.status,
        "total_requests": deployment.total_requests,
        "last_request_at": deployment.last_request_at,
        "created_at": deployment.created_at,
        "deployed_at": deployment.deployed_at,
        "endpoint_url": f"/api/deployed{deployment.endpoint_path}"
    }


@router.get("/stats/")
async def get_deployment_stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get summary statistics for all user deployments."""
    
    # Get all user deployments
    query = select(ApiDeployment).where(
        ApiDeployment.user_id == current_user.id
    )
    result = await db.execute(query)
    deployments = result.scalars().all()
    
    # Calculate statistics
    total_requests = sum(d.total_requests for d in deployments)
    active_deployments = len([d for d in deployments if d.status == DeploymentStatus.ACTIVE])
    
    # Calculate average response time (placeholder - would need actual metrics)
    average_response_time = 0
    if deployments:
        # In a real implementation, this would query actual metrics
        average_response_time = 250  # milliseconds placeholder
    
    return {
        "total_deployments": len(deployments),
        "active_deployments": active_deployments,
        "total_requests": total_requests,
        "average_response_time": average_response_time
    }