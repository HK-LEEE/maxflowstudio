"""
WebSocket handlers for interactive flow testing
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.core.database import get_db
from src.core.auth import get_current_user_ws
from src.models.flow import Flow, FlowVersion
from src.models.execution import Execution, ExecutionStatus
from src.core.interactive_workflow_engine import InteractiveOrchestrator
from sqlalchemy import select

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for flow test sessions"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        logger.info("WebSocket connected", session_id=session_id, user_id=user_id)
        
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            # Remove user session mapping
            for user_id, sid in list(self.user_sessions.items()):
                if sid == session_id:
                    del self.user_sessions[user_id]
                    break
        logger.info("WebSocket disconnected", session_id=session_id)
        
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
            
    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            await self.send_message(session_id, message)


manager = ConnectionManager()


class FlowTestSession:
    """Manages an interactive flow test session"""
    
    def __init__(self, session_id: str, flow_id: str, user_id: str, db: AsyncSession):
        self.session_id = session_id
        self.flow_id = flow_id
        self.user_id = user_id
        self.db = db
        self.execution_id: Optional[str] = None
        self.orchestrator: Optional[InteractiveOrchestrator] = None
        self.is_active = True
        
    async def start(self, flow_definition: dict):
        """Start the flow test session"""
        try:
            # Create execution record
            self.execution_id = str(uuid.uuid4())
            execution = Execution(
                id=self.execution_id,
                flow_id=self.flow_id,
                user_id=self.user_id,
                status=ExecutionStatus.RUNNING,
                inputs={},
                started_at=datetime.utcnow()
            )
            self.db.add(execution)
            await self.db.commit()
            
            # Initialize interactive orchestrator
            self.orchestrator = InteractiveOrchestrator(
                execution_id=self.execution_id,
                flow_definition=flow_definition,
                flow_id=self.flow_id,
                user_id=self.user_id,
                on_node_start=self._on_node_start,
                on_node_complete=self._on_node_complete,
                on_node_error=self._on_node_error,
                on_input_required=self._on_input_required,
                on_output=self._on_output,
                on_streaming_update=self._on_streaming_update
            )
            
            # Send session started message
            await manager.send_message(self.session_id, {
                "type": "session_started",
                "execution_id": self.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Start execution
            await self.orchestrator.execute()
            
        except Exception as e:
            logger.error("Failed to start test session", error=str(e))
            await manager.send_message(self.session_id, {
                "type": "error",
                "message": f"Failed to start test session: {str(e)}"
            })
            
    async def handle_user_input(self, node_id: str, input_data: dict):
        """Handle user input for a specific node"""
        logger.info("Handling user input", node_id=node_id, input_data=input_data)
        if self.orchestrator:
            await self.orchestrator.provide_input(node_id, input_data)
            logger.info("User input provided to orchestrator", node_id=node_id)
        else:
            logger.warning("No orchestrator available for user input", node_id=node_id)
            
    async def restart_with_input(self, user_message: str):
        """Restart flow execution with user input"""
        try:
            # Stop current execution if running
            if self.orchestrator:
                await self.orchestrator.cancel()
            
            # Create a new execution for each restart
            new_execution = Execution(
                id=str(uuid.uuid4()),
                flow_id=self.flow_id,
                user_id=self.user_id,
                status=ExecutionStatus.RUNNING,
                inputs={"user_message": user_message},
                started_at=datetime.utcnow()
            )
            self.db.add(new_execution)
            await self.db.commit()
            
            # Update execution ID
            self.execution_id = new_execution.id
            
            # Get flow definition with input nodes
            flow_definition = self.orchestrator.flow_definition if self.orchestrator else {}
            
            # Find input nodes and inject user message
            if "nodes" in flow_definition:
                for node in flow_definition["nodes"]:
                    if node.get("data", {}).get("type") == "input":
                        # Inject user message into input node
                        if "data" not in node:
                            node["data"] = {}
                        if "config" not in node["data"]:
                            node["data"]["config"] = {}
                        node["data"]["config"]["default_value"] = user_message
                        node["data"]["config"]["input_value"] = user_message
            
            # Reinitialize orchestrator with new execution ID
            self.orchestrator = InteractiveOrchestrator(
                execution_id=new_execution.id,
                flow_definition=flow_definition,
                flow_id=self.flow_id,
                user_id=self.user_id,
                on_node_start=self._on_node_start,
                on_node_complete=self._on_node_complete,
                on_node_error=self._on_node_error,
                on_input_required=self._on_input_required,
                on_output=self._on_output,
                on_streaming_update=self._on_streaming_update
            )
            
            # Send flow restart message
            await manager.send_message(self.session_id, {
                "type": "flow_restarted",
                "message": user_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Start execution
            await self.orchestrator.execute()
            
        except Exception as e:
            logger.error("Failed to restart flow with input", error=str(e))
            await manager.send_message(self.session_id, {
                "type": "error",
                "message": f"Failed to restart flow: {str(e)}"
            })
            
    async def stop(self):
        """Stop the test session"""
        self.is_active = False
        if self.orchestrator:
            await self.orchestrator.cancel()
            
        # Update execution status
        if self.execution_id:
            execution = await self.db.get(Execution, self.execution_id)
            if execution:
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
                await self.db.commit()
                
    async def _on_node_start(self, node_id: str, node_type: str, node_label: str):
        """Called when a node starts executing"""
        await manager.send_message(self.session_id, {
            "type": "node_start",
            "node_id": node_id,
            "node_type": node_type,
            "node_label": node_label,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _on_node_complete(self, node_id: str, result: dict):
        """Called when a node completes execution"""
        await manager.send_message(self.session_id, {
            "type": "node_complete",
            "node_id": node_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _on_node_error(self, node_id: str, error: str):
        """Called when a node encounters an error"""
        await manager.send_message(self.session_id, {
            "type": "node_error",
            "node_id": node_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _on_input_required(self, node_id: str, input_schema: dict):
        """Called when a node requires user input"""
        await manager.send_message(self.session_id, {
            "type": "input_required",
            "node_id": node_id,
            "input_schema": input_schema,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _on_output(self, node_id: str, output_data: dict):
        """Called when a node produces output"""
        # Check if this is an output node
        node_type = None
        if self.orchestrator and hasattr(self.orchestrator, 'nodes'):
            node = self.orchestrator.nodes.get(node_id)
            if node:
                node_type = node.type
        
        await manager.send_message(self.session_id, {
            "type": "node_output",
            "node_id": node_id,
            "node_type": node_type,
            "output": output_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _on_streaming_update(self, node_id: str, update_data: dict):
        """Called when a node emits a streaming update"""
        await manager.send_message(self.session_id, {
            "type": "streaming_update",
            "node_id": node_id,
            "node_type": update_data.get("node_type", "unknown"),
            "node_label": update_data.get("node_label"),
            "delta": update_data.get("delta", ""),
            "accumulated": update_data.get("accumulated", ""),
            "is_complete": update_data.get("is_complete", False),
            "timestamp": datetime.utcnow().isoformat()
        })


async def websocket_flow_test(
    websocket: WebSocket,
    flow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for interactive flow testing"""
    session_id = str(uuid.uuid4())
    test_session: Optional[FlowTestSession] = None
    
    try:
        # Authenticate user from WebSocket
        user = await get_current_user_ws(websocket, db)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return
            
        # Connect WebSocket
        await manager.connect(websocket, session_id, user.id)
        
        # Verify flow access
        flow = await db.get(Flow, flow_id)
        if not flow or flow.user_id != user.id:
            await websocket.close(code=4004, reason="Flow not found")
            return
            
        # Get flow definition
        version_result = await db.execute(
            select(FlowVersion).where(
                FlowVersion.flow_id == flow_id,
                FlowVersion.version_number == flow.current_version
            )
        )
        flow_version = version_result.scalar_one_or_none()
        
        if not flow_version:
            await websocket.close(code=4004, reason="Flow version not found")
            return
            
        # Create test session
        test_session = FlowTestSession(session_id, flow_id, user.id, db)
        
        # Send initial connection success message
        await manager.send_message(session_id, {
            "type": "connected",
            "flow_id": flow_id,
            "flow_name": flow.name,
            "session_id": session_id
        })
        
        # Start the test session (non-blocking)
        asyncio.create_task(test_session.start(flow_version.definition))
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            logger.info("Received WebSocket message", message_type=message_type, data=data)
            
            if message_type == "flow_input":
                # Handle flow input - restart flow execution with user input
                message = data.get("message", "")
                await test_session.restart_with_input(message)
                
            elif message_type == "user_input":
                node_id = data.get("node_id")
                input_data = data.get("input", data.get("input_data", {}))
                logger.info("Received user input", node_id=node_id, input_data=input_data)
                if node_id:
                    await test_session.handle_user_input(node_id, input_data)
                    logger.info("User input handled", node_id=node_id)
                    
            elif message_type == "stop":
                await test_session.stop()
                break
                
            elif message_type == "ping":
                await manager.send_message(session_id, {"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id)
        await websocket.close(code=4000, reason=str(e))
    finally:
        # Cleanup
        if test_session:
            await test_session.stop()
        manager.disconnect(session_id)