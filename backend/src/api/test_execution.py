"""
Test endpoint for flow execution
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.workflow_engine import orchestrator
from src.models.flow import Flow, FlowVersion
from src.models.execution import Execution, ExecutionStatus
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/test-execution")
async def test_execution(db: AsyncSession = Depends(get_db)):
    """Test flow execution with a simple flow"""
    
    # Create a test flow
    test_flow_definition = {
        "nodes": [
            {
                "id": "node1",
                "type": "input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "type": "input",
                    "label": "Test Input",
                    "config": {"default_value": "Hello World"}
                }
            },
            {
                "id": "node2",
                "type": "transform",
                "position": {"x": 300, "y": 100},
                "data": {
                    "type": "transform",
                    "label": "Transform",
                    "config": {
                        "transform_type": "template",
                        "transform_expression": "Transformed: {value}"
                    }
                }
            },
            {
                "id": "node3",
                "type": "output",
                "position": {"x": 500, "y": 100},
                "data": {
                    "type": "output",
                    "label": "Test Output",
                    "config": {}
                }
            }
        ],
        "edges": [
            {
                "id": "edge1",
                "source": "node1",
                "target": "node2",
                "sourceHandle": "output",
                "targetHandle": "input"
            },
            {
                "id": "edge2",
                "source": "node2",
                "target": "node3",
                "sourceHandle": "output",
                "targetHandle": "input"
            }
        ]
    }
    
    # Create test flow
    flow = Flow(
        id=str(uuid.uuid4()),
        name="Test Flow",
        description="Test flow for execution",
        user_id="test-user",
        current_version=1
    )
    db.add(flow)
    
    # Create flow version
    version = FlowVersion(
        id=str(uuid.uuid4()),
        flow_id=flow.id,
        version_number=1,
        definition=test_flow_definition,
        change_summary="Initial test version",
        created_by="test-user"
    )
    db.add(version)
    
    # Create execution
    execution = Execution(
        id=str(uuid.uuid4()),
        flow_id=flow.id,
        user_id="test-user",
        status=ExecutionStatus.PENDING,
        inputs={"test": "data"},
        started_at=datetime.utcnow()
    )
    db.add(execution)
    
    await db.commit()
    
    # Execute flow
    try:
        await orchestrator.execute_flow(execution.id)
        
        # Refresh execution to get results
        await db.refresh(execution)
        
        return {
            "status": "success",
            "execution_id": execution.id,
            "flow_id": flow.id,
            "result": execution.outputs,
            "execution_status": execution.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "execution_id": execution.id
        }