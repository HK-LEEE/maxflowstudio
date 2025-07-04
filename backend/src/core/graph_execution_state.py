"""
Graph Execution State Management
Flow: State initialization → Status tracking → Context management → Result collection
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import structlog
from pydantic import BaseModel, Field

from .component_base import BaseComponent, ComponentResult, ComponentStatus

logger = structlog.get_logger()


class ExecutionStatus(str, Enum):
    """Graph execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeExecutionStatus(str, Enum):
    """Individual node execution status."""
    PENDING = "pending"
    WAITING = "waiting"      # Waiting for dependencies
    READY = "ready"          # Ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeExecutionResult:
    """Result of a single node execution."""
    node_id: str
    component_type: str
    status: NodeExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    component_result: Optional[ComponentResult] = None


@dataclass
class GraphExecutionContext:
    """
    Execution context for graph processing.
    
    Context Management:
    1. initialize() → Set up execution environment
    2. track_node_state() → Monitor individual node progress
    3. manage_data_flow() → Handle inter-node data transfer
    4. collect_results() → Aggregate execution outcomes
    
    Responsibilities:
    - Node state and status tracking
    - Data flow between nodes
    - Error propagation and handling
    - Execution timeline management
    """
    
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    flow_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Node execution tracking
    node_results: Dict[str, NodeExecutionResult] = field(default_factory=dict)
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Execution context and shared data
    global_context: Dict[str, Any] = field(default_factory=dict)
    execution_variables: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize context after creation."""
        self.logger = logger.bind(
            execution_id=self.execution_id,
            flow_id=self.flow_id
        )
    
    def start_execution(self) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self.logger.info("Graph execution started")
    
    def complete_execution(self) -> None:
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.end_time = datetime.utcnow()
        self.logger.info("Graph execution completed")
    
    def fail_execution(self, error: str) -> None:
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.end_time = datetime.utcnow()
        self.errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "execution_failure",
            "message": error
        })
        self.logger.error("Graph execution failed", error=error)
    
    def cancel_execution(self) -> None:
        """Mark execution as cancelled."""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = datetime.utcnow()
        self.logger.info("Graph execution cancelled")
    
    def start_node_execution(self, node_id: str, component_type: str) -> None:
        """Start execution of a specific node."""
        if node_id not in self.node_results:
            self.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                component_type=component_type,
                status=NodeExecutionStatus.PENDING
            )
        
        result = self.node_results[node_id]
        result.status = NodeExecutionStatus.RUNNING
        result.start_time = datetime.utcnow()
        
        self.logger.info("Node execution started", node_id=node_id, component_type=component_type)
    
    def complete_node_execution(
        self, 
        node_id: str, 
        outputs: Dict[str, Any], 
        component_result: ComponentResult = None
    ) -> None:
        """Complete execution of a specific node."""
        if node_id not in self.node_results:
            raise ValueError(f"Node {node_id} not found in execution context")
        
        result = self.node_results[node_id]
        result.status = NodeExecutionStatus.COMPLETED
        result.end_time = datetime.utcnow()
        result.outputs = outputs
        result.component_result = component_result
        
        if result.start_time:
            result.execution_time = (result.end_time - result.start_time).total_seconds()
        
        # Store outputs for other nodes to access
        self.node_outputs[node_id] = outputs
        
        self.logger.info(
            "Node execution completed", 
            node_id=node_id, 
            execution_time=result.execution_time
        )
    
    def fail_node_execution(self, node_id: str, error: str) -> None:
        """Mark node execution as failed."""
        if node_id not in self.node_results:
            self.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                component_type="unknown",
                status=NodeExecutionStatus.PENDING
            )
        
        result = self.node_results[node_id]
        result.status = NodeExecutionStatus.FAILED
        result.end_time = datetime.utcnow()
        result.error_message = error
        
        if result.start_time:
            result.execution_time = (result.end_time - result.start_time).total_seconds()
        
        # Add to global errors
        self.errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "node_execution_error",
            "node_id": node_id,
            "message": error
        })
        
        self.logger.error("Node execution failed", node_id=node_id, error=error)
    
    def skip_node_execution(self, node_id: str, reason: str) -> None:
        """Mark node as skipped."""
        if node_id not in self.node_results:
            self.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                component_type="unknown",
                status=NodeExecutionStatus.PENDING
            )
        
        result = self.node_results[node_id]
        result.status = NodeExecutionStatus.SKIPPED
        result.error_message = reason
        
        self.logger.info("Node execution skipped", node_id=node_id, reason=reason)
    
    def get_node_outputs(self, node_id: str) -> Dict[str, Any]:
        """Get outputs from a specific node."""
        return self.node_outputs.get(node_id, {})
    
    def set_execution_variable(self, key: str, value: Any) -> None:
        """Set a shared execution variable."""
        self.execution_variables[key] = value
        self.logger.debug("Execution variable set", key=key)
    
    def get_execution_variable(self, key: str, default: Any = None) -> Any:
        """Get a shared execution variable."""
        return self.execution_variables.get(key, default)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution results."""
        total_nodes = len(self.node_results)
        completed_nodes = sum(1 for r in self.node_results.values() 
                            if r.status == NodeExecutionStatus.COMPLETED)
        failed_nodes = sum(1 for r in self.node_results.values() 
                         if r.status == NodeExecutionStatus.FAILED)
        
        total_time = None
        if self.start_time and self.end_time:
            total_time = (self.end_time - self.start_time).total_seconds()
        
        return {
            "execution_id": self.execution_id,
            "flow_id": self.flow_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_execution_time": total_time,
            "total_nodes": total_nodes,
            "completed_nodes": completed_nodes,
            "failed_nodes": failed_nodes,
            "success_rate": completed_nodes / total_nodes if total_nodes > 0 else 0,
            "error_count": len(self.errors),
            "has_errors": len(self.errors) > 0
        }