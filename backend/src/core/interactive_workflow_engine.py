"""
Interactive Workflow Engine for real-time flow testing with user interaction
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime
import structlog

from src.core.workflow_engine import FlowNode, FlowEdge, Task, TaskStatus, DAGAnalyzer
from src.workers import get_worker
from src.workers.base_worker import ExecutionContext

logger = structlog.get_logger(__name__)


class InteractiveOrchestrator:
    """Orchestrates interactive flow execution with user input support"""
    
    def __init__(
        self,
        execution_id: str,
        flow_definition: dict,
        flow_id: str = None,
        user_id: str = None,
        on_node_start: Callable = None,
        on_node_complete: Callable = None,
        on_node_error: Callable = None,
        on_input_required: Callable = None,
        on_output: Callable = None,
        on_streaming_update: Callable = None
    ):
        self.execution_id = execution_id
        self.flow_definition = flow_definition
        self.flow_id = flow_id
        self.user_id = user_id
        self.on_node_start = on_node_start
        self.on_node_complete = on_node_complete
        self.on_node_error = on_node_error
        self.on_input_required = on_input_required
        self.on_output = on_output
        self.on_streaming_update = on_streaming_update
        
        # Parse flow definition
        self.nodes = self._parse_nodes(flow_definition.get("nodes", []))
        self.edges = self._parse_edges(flow_definition.get("edges", []))
        
        # Initialize DAG analyzer
        self.dag = DAGAnalyzer(list(self.nodes.values()), self.edges)
        
        # Execution state
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: Set[str] = set()
        self.user_inputs: Dict[str, asyncio.Event] = {}
        self.user_input_data: Dict[str, Any] = {}
        self.is_cancelled = False
        
    def _parse_nodes(self, nodes_data: List[dict]) -> Dict[str, FlowNode]:
        """Parse nodes from flow definition"""
        nodes = {}
        for node_data in nodes_data:
            # Prioritize the actual node type from data.type over the ReactFlow type
            actual_type = node_data.get("data", {}).get("type")
            if not actual_type:
                # Fallback to the top-level type if data.type is not available
                actual_type = node_data.get("type", "unknown")
            
            node = FlowNode(
                id=node_data["id"],
                type=actual_type,
                data=node_data.get("data", {}),
                position=node_data.get("position", {"x": 0, "y": 0})
            )
            nodes[node.id] = node
        return nodes
        
    def _parse_edges(self, edges_data: List[dict]) -> List[FlowEdge]:
        """Parse edges from flow definition"""
        edges = []
        for edge_data in edges_data:
            edge = FlowEdge(
                id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                source_handle=edge_data.get("sourceHandle"),
                target_handle=edge_data.get("targetHandle")
            )
            edges.append(edge)
        return edges
        
    async def execute(self):
        """Execute the flow interactively"""
        try:
            # Create tasks from nodes
            self._create_tasks()
            
            # Get execution order
            execution_order = self.dag.topological_sort()
            
            # Execute tasks in order
            for node_id in execution_order:
                if self.is_cancelled:
                    break
                    
                task = self.tasks[node_id]
                await self._execute_task(task)
                
        except Exception as e:
            logger.error("Flow execution failed", error=str(e))
            raise
            
    def _create_tasks(self):
        """Create tasks from nodes"""
        for node_id, node in self.nodes.items():
            # Get dependencies and input mappings
            dependencies = []
            input_mappings = {}
            
            for edge in self.edges:
                if edge.target == node_id:
                    dependencies.append(edge.source)
                    target_handle = edge.target_handle or "input"
                    source_handle = edge.source_handle or "output"
                    input_mappings[target_handle] = (edge.source, source_handle)
                    
            task = Task(
                id=f"task_{node_id}",
                node_id=node_id,
                node_type=node.type,
                config=node.data.get("config", {}),
                inputs={},
                dependencies=dependencies,
                input_mappings=input_mappings
            )
            
            self.tasks[node_id] = task
            
    async def _execute_task(self, task: Task):
        """Execute a single task"""
        try:
            # Notify node start
            node = self.nodes[task.node_id]
            if self.on_node_start:
                await self.on_node_start(
                    task.node_id,
                    node.type,
                    node.data.get("label", "Unknown")
                )
                
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Gather inputs from dependencies
            task.inputs = await self._gather_task_inputs(task)
            
            # Check if node requires user input
            if node.type == "input" or node.data.get("requiresUserInput"):
                # Skip user input if default value is provided
                config = node.data.get("config", {})
                has_default = config.get("default_value") or config.get("input_value")
                if not has_default:
                    await self._handle_user_input(task)
                
            # Execute the task
            worker = get_worker(task.node_type)
            if worker:
                # Set orchestrator reference for streaming support
                if hasattr(worker, 'set_orchestrator'):
                    worker.set_orchestrator(self)
                
                # Create execution context
                context = ExecutionContext(
                    execution_id=self.execution_id,
                    flow_id=self.flow_id or "unknown",
                    node_id=task.node_id,
                    user_id=self.user_id
                )
                
                result = await worker.execute(
                    config=task.config,
                    inputs=task.inputs,
                    context=context
                )
                task.result = result
                task.status = TaskStatus.COMPLETED
                
                # Send output notification
                if self.on_output and result:
                    await self.on_output(task.node_id, result)
                    
            else:
                raise ValueError(f"No worker found for node type: {task.node_type}")
                
            # Update task completion
            task.completed_at = datetime.utcnow()
            self.completed_tasks.add(task.node_id)
            
            # Notify node complete
            if self.on_node_complete:
                await self.on_node_complete(task.node_id, task.result)
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            # Notify node error
            if self.on_node_error:
                await self.on_node_error(task.node_id, str(e))
                
            logger.error("Task execution failed", task_id=task.id, error=str(e))
            raise
            
    async def _gather_task_inputs(self, task: Task) -> Dict[str, Any]:
        """Gather inputs for a task from its dependencies"""
        inputs = {}
        
        for target_handle, (source_node_id, source_handle) in task.input_mappings.items():
            source_task = self.tasks.get(source_node_id)
            if source_task and source_task.result:
                # Get the specific output from the source task
                if isinstance(source_task.result, dict):
                    if source_handle in source_task.result:
                        inputs[target_handle] = source_task.result[source_handle]
                    elif "output" in source_task.result:
                        inputs[target_handle] = source_task.result["output"]
                    else:
                        inputs[target_handle] = source_task.result
                else:
                    inputs[target_handle] = source_task.result
                    
        return inputs
        
    async def _handle_user_input(self, task: Task):
        """Handle user input requirement for a task"""
        node = self.nodes[task.node_id]
        
        # Create event for waiting on user input
        event = asyncio.Event()
        self.user_inputs[task.node_id] = event
        
        # Notify that input is required
        if self.on_input_required:
            input_schema = node.data.get("inputSchema", {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "title": node.data.get("label", "Input"),
                        "description": node.data.get("description", "Please provide input")
                    }
                }
            })
            await self.on_input_required(task.node_id, input_schema)
            
        # Wait for user input
        await event.wait()
        
        # Get the provided input
        if task.node_id in self.user_input_data:
            task.inputs.update(self.user_input_data[task.node_id])
            del self.user_input_data[task.node_id]
            
    async def provide_input(self, node_id: str, input_data: dict):
        """Provide user input for a waiting node"""
        if node_id in self.user_inputs:
            self.user_input_data[node_id] = input_data
            self.user_inputs[node_id].set()
            del self.user_inputs[node_id]
            
    async def cancel(self):
        """Cancel the execution"""
        self.is_cancelled = True
        
        # Clear any waiting user inputs
        for event in self.user_inputs.values():
            event.set()
            
    async def emit_streaming_update(
        self, 
        node_id: str, 
        node_type: str = "unknown",
        node_label: str = None,
        delta: str = "",
        accumulated: str = "",
        is_complete: bool = False
    ):
        """Emit streaming update for real-time response"""
        if self.on_streaming_update:
            try:
                await self.on_streaming_update(
                    node_id=node_id,
                    update_data={
                        "node_type": node_type,
                        "node_label": node_label,
                        "delta": delta,
                        "accumulated": accumulated,
                        "is_complete": is_complete
                    }
                )
            except Exception as e:
                logger.warning(
                    "Failed to emit streaming update",
                    node_id=node_id,
                    error=str(e)
                )