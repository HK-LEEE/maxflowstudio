"""
Flow execution endpoints
Flow: Start -> Queue -> Execute -> Results
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.core.database import get_db
from src.core.auth import get_current_user
from src.models.execution import Execution, ExecutionStatus
from src.models.flow import Flow
from src.models.user import User

router = APIRouter()


# Pydantic schemas
class ExecutionStart(BaseModel):
    flowId: str
    inputs: Optional[dict] = None


class ExecutionResponse(BaseModel):
    id: str
    flow_id: str
    user_id: str
    status: ExecutionStatus
    inputs: Optional[dict]
    outputs: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration: Optional[float] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ExecutionResponse])
async def list_executions(
    flow_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List executions for the current user."""
    query = select(Execution).where(Execution.user_id == current_user.id)
    
    if flow_id:
        query = query.where(Execution.flow_id == flow_id)
    
    query = query.order_by(Execution.created_at.desc())
    
    result = await db.execute(query)
    executions = result.scalars().all()
    
    # Duration is automatically calculated by the property method
    
    return executions


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific execution."""
    result = await db.execute(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.user_id == current_user.id
        )
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Duration is automatically calculated by the property method
    
    return execution


@router.post("/start", response_model=ExecutionResponse)
async def start_execution(
    execution_data: ExecutionStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new flow execution."""
    # Verify flow exists and belongs to user
    flow_result = await db.execute(
        select(Flow).where(
            Flow.id == execution_data.flowId,
            Flow.user_id == current_user.id
        )
    )
    flow = flow_result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Create execution record
    execution_id = str(uuid.uuid4())
    execution = Execution(
        id=execution_id,
        flow_id=execution_data.flowId,
        user_id=current_user.id,
        status=ExecutionStatus.PENDING,
        inputs=execution_data.inputs,
        started_at=datetime.utcnow()
    )
    
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    
    # Start workflow execution asynchronously
    import asyncio
    
    # Try to use queued orchestrator if available, fallback to direct execution
    async def execute_workflow():
        try:
            from src.core.queued_workflow_engine import queued_orchestrator
            if queued_orchestrator:
                await queued_orchestrator.execute_flow(execution_id)
            else:
                # Fallback to direct execution
                from src.core.workflow_engine import orchestrator
                await orchestrator.execute_flow(execution_id)
        except Exception as e:
            # Error handling is done within the orchestrator
            pass
    
    # Start the workflow execution in the background
    asyncio.create_task(execute_workflow())
    
    await db.refresh(execution)
    
    return execution


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running execution."""
    # Get execution
    result = await db.execute(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.user_id == current_user.id
        )
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="Execution cannot be cancelled")
    
    # Cancel execution
    execution.status = ExecutionStatus.CANCELLED
    execution.completed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Execution cancelled successfully"}