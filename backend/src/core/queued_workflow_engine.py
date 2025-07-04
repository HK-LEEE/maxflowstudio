"""
Queued Workflow Engine - Uses RabbitMQ for task distribution
Flow: Flow Definition -> DAG Analysis -> Task Publishing -> Queue Processing -> Result Collection
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.workflow_engine import (
    DAGAnalyzer, FlowNode, FlowEdge, Task, TaskStatus, 
    WorkflowOrchestrator as BaseOrchestrator
)
from src.core.message_queue import MessageQueue, TaskMessage, QueuedTaskExecutor
from src.models.execution import Execution, ExecutionStatus
from src.models.flow import FlowVersion
from src.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


class QueuedWorkflowOrchestrator(BaseOrchestrator):
    """Workflow orchestrator that uses message queues for task distribution."""
    
    def __init__(self, message_queue: MessageQueue):
        super().__init__()
        self.mq = message_queue
        self.executor = QueuedTaskExecutor(message_queue)
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.task_results: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.result_consumer_started = False
    
    async def execute_flow(self, execution_id: str) -> None:
        """Execute a flow using message queue."""
        async with AsyncSessionLocal() as db:
            try:
                # Get execution and flow data
                execution = await self._get_execution(db, execution_id)
                if not execution:
                    raise ValueError(f"Execution {execution_id} not found")
                
                flow_version = await self._get_flow_version(db, execution.flow_id)
                if not flow_version or not flow_version.definition:
                    raise ValueError(f"Flow definition not found for execution {execution_id}")
                
                # Update execution status
                await self._update_execution_status(db, execution_id, ExecutionStatus.RUNNING)
                
                # Parse flow definition
                flow_def = flow_version.definition
                nodes = [FlowNode(**node) for node in flow_def.get('nodes', [])]
                edges = [FlowEdge(**edge) for edge in flow_def.get('edges', [])]
                
                # Analyze DAG
                dag = DAGAnalyzer(nodes, edges)
                if not dag.validate_dag():
                    raise ValueError("Flow contains cycles - not a valid DAG")
                
                # Create tasks
                tasks = self._create_tasks(nodes, edges, execution.inputs or {})
                
                # Store execution state
                self.active_executions[execution_id] = {
                    "tasks": tasks,
                    "dag": dag,
                    "completed_nodes": set(),
                    "started_at": datetime.utcnow(),
                    "flow_id": execution.flow_id
                }
                
                # Start result consumer if not already started
                if not self.result_consumer_started:
                    await self.start_result_consumer()
                
                # Start workflow execution
                await self._schedule_initial_tasks(execution_id)
                
            except Exception as e:
                self.logger.error("Queued workflow execution failed", execution_id=execution_id, error=str(e))
                await self._fail_execution(db, execution_id, str(e))
                raise
    
    async def start_result_consumer(self) -> None:
        """Start consuming task results."""
        if not self.mq.channel:
            raise RuntimeError("Message queue not connected")
        
        result_queue = await self.mq.channel.get_queue(self.mq.result_queue_name)
        
        async def process_result(message) -> None:
            async with message.process():
                try:
                    import json
                    result_data = json.loads(message.body.decode())
                    await self._handle_task_result(result_data)
                except Exception as e:
                    self.logger.error("Failed to process result", error=str(e))
                    raise
        
        await result_queue.consume(process_result)
        self.result_consumer_started = True
        self.logger.info("Result consumer started")
    
    async def _schedule_initial_tasks(self, execution_id: str) -> None:
        """Schedule initial tasks that have no dependencies."""
        execution_state = self.active_executions[execution_id]
        dag = execution_state["dag"]
        tasks = execution_state["tasks"]
        completed_nodes = execution_state["completed_nodes"]
        
        # Get initial executable nodes
        executable_nodes = dag.get_executable_nodes(completed_nodes)
        
        for node_id in executable_nodes:
            task = tasks[node_id]
            await self._publish_task(execution_id, task)
    
    async def _publish_task(self, execution_id: str, task: Task) -> None:
        """Publish a task to the message queue."""
        execution_state = self.active_executions[execution_id]
        
        task_message = TaskMessage(
            task_id=task.id,
            execution_id=execution_id,
            flow_id=execution_state["flow_id"],
            node_id=task.node_id,
            node_type=task.node_type,
            config=task.config,
            inputs=task.inputs,
            dependencies=task.dependencies,
            created_at=datetime.utcnow().isoformat()
        )
        
        await self.mq.publish_task(task_message)
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        self.logger.info(
            "Task published to queue",
            execution_id=execution_id,
            task_id=task.id,
            node_type=task.node_type
        )
    
    async def _handle_task_result(self, result_data: Dict[str, Any]) -> None:
        """Handle task completion result."""
        task_id = result_data["task_id"]
        execution_id = result_data["execution_id"]
        success = result_data["success"]
        result = result_data["result"]
        
        if execution_id not in self.active_executions:
            self.logger.warning("Received result for unknown execution", execution_id=execution_id)
            return
        
        execution_state = self.active_executions[execution_id]
        tasks = execution_state["tasks"]
        dag = execution_state["dag"]
        completed_nodes = execution_state["completed_nodes"]
        
        # Find the task and node
        task = None
        node_id = None
        for nid, t in tasks.items():
            if t.id == task_id:
                task = t
                node_id = nid
                break
        
        if not task:
            self.logger.warning("Received result for unknown task", task_id=task_id)
            return
        
        # Update task status
        task.completed_at = datetime.utcnow()
        
        if success:
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.task_results[execution_id][node_id] = result
            completed_nodes.add(node_id)
            
            self.logger.info(
                "Task completed successfully",
                execution_id=execution_id,
                task_id=task_id,
                node_id=node_id
            )
            
            # Schedule next tasks
            await self._schedule_next_tasks(execution_id)
            
        else:
            task.status = TaskStatus.FAILED
            task.error = result.get("error", "Unknown error")
            
            self.logger.error(
                "Task failed",
                execution_id=execution_id,
                task_id=task_id,
                error=task.error
            )
            
            # Fail the entire execution
            async with AsyncSessionLocal() as db:
                await self._fail_execution(db, execution_id, f"Task {task_id} failed: {task.error}")
            
            # Clean up execution state
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _schedule_next_tasks(self, execution_id: str) -> None:
        """Schedule next available tasks."""
        execution_state = self.active_executions[execution_id]
        dag = execution_state["dag"]
        tasks = execution_state["tasks"]
        completed_nodes = execution_state["completed_nodes"]
        
        # Get newly executable nodes
        executable_nodes = dag.get_executable_nodes(completed_nodes)
        
        # Filter out already running/completed tasks
        newly_executable = []
        for node_id in executable_nodes:
            task = tasks[node_id]
            if task.status == TaskStatus.PENDING:
                newly_executable.append(node_id)
        
        # Schedule new tasks
        for node_id in newly_executable:
            task = tasks[node_id]
            # Prepare inputs from completed dependencies
            task_inputs = task.inputs.copy() if task.inputs else {}
            for dep_node_id in task.dependencies:
                if dep_node_id in self.task_results[execution_id]:
                    task_inputs[dep_node_id] = self.task_results[execution_id][dep_node_id]
            
            task.inputs = task_inputs
            await self._publish_task(execution_id, task)
        
        # Check if workflow is complete
        if len(completed_nodes) == len(tasks):
            await self._complete_workflow(execution_id)
    
    async def _complete_workflow(self, execution_id: str) -> None:
        """Complete the workflow execution."""
        execution_state = self.active_executions[execution_id]
        results = self.task_results[execution_id]
        
        async with AsyncSessionLocal() as db:
            await self._complete_execution(db, execution_id, results)
        
        # Clean up state
        del self.active_executions[execution_id]
        if execution_id in self.task_results:
            del self.task_results[execution_id]
        
        self.logger.info(
            "Workflow completed",
            execution_id=execution_id,
            duration=(datetime.utcnow() - execution_state["started_at"]).total_seconds()
        )
    
    def _create_tasks(self, nodes: List[FlowNode], edges: List[FlowEdge], flow_inputs: Dict[str, Any]) -> Dict[str, Task]:
        """Create tasks with unique IDs for queue processing."""
        tasks = {}
        
        # Build dependency map
        dependencies = {node.id: [] for node in nodes}
        for edge in edges:
            dependencies[edge.target].append(edge.source)
        
        for node in nodes:
            task_id = f"task_{node.id}_{uuid.uuid4().hex[:8]}"
            task = Task(
                id=task_id,
                node_id=node.id,
                node_type=node.type,
                config=node.data,
                inputs=flow_inputs if node.type == 'input' else {},
                dependencies=dependencies[node.id]
            )
            tasks[node.id] = task
        
        return tasks


# Create global instance (will be initialized with message queue)
queued_orchestrator: Optional[QueuedWorkflowOrchestrator] = None


async def initialize_queued_orchestrator(message_queue: MessageQueue) -> QueuedWorkflowOrchestrator:
    """Initialize the queued orchestrator."""
    global queued_orchestrator
    queued_orchestrator = QueuedWorkflowOrchestrator(message_queue)
    return queued_orchestrator