"""
Workflow Engine - Core orchestration logic
Flow: Flow Definition -> DAG Analysis -> Task Scheduling -> Execution
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution import Execution, ExecutionStatus
from src.models.flow import Flow, FlowVersion
from src.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FlowNode:
    """Represents a node in the flow."""
    id: str
    type: str
    data: Dict[str, Any]
    position: Dict[str, float]


@dataclass
class FlowEdge:
    """Represents an edge/connection between nodes."""
    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


@dataclass
class Task:
    """Represents an executable task."""
    id: str
    node_id: str
    node_type: str
    config: Dict[str, Any]
    inputs: Dict[str, Any]
    dependencies: List[str]
    input_mappings: Dict[str, tuple[str, str]]  # target_handle -> (source_node, source_handle)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DAGAnalyzer:
    """Analyzes flow definition and creates a directed acyclic graph."""
    
    def __init__(self, nodes: List[FlowNode], edges: List[FlowEdge]):
        self.nodes = {node.id: node for node in nodes}
        self.edges = edges
        self.adjacency_list = self._build_adjacency_list()
        self.reverse_adjacency_list = self._build_reverse_adjacency_list()
    
    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """Build adjacency list for forward dependencies."""
        adj_list = {node_id: [] for node_id in self.nodes.keys()}
        for edge in self.edges:
            adj_list[edge.source].append(edge.target)
        return adj_list
    
    def _build_reverse_adjacency_list(self) -> Dict[str, List[str]]:
        """Build reverse adjacency list for backward dependencies."""
        rev_adj_list = {node_id: [] for node_id in self.nodes.keys()}
        for edge in self.edges:
            rev_adj_list[edge.target].append(edge.source)
        return rev_adj_list
    
    def topological_sort(self) -> List[str]:
        """Return nodes in topological order."""
        visited = set()
        temp_visited = set()
        result = []
        
        def dfs(node_id: str):
            if node_id in temp_visited:
                raise ValueError(f"Cycle detected involving node {node_id}")
            if node_id in visited:
                return
            
            temp_visited.add(node_id)
            for neighbor in self.adjacency_list[node_id]:
                dfs(neighbor)
            
            temp_visited.remove(node_id)
            visited.add(node_id)
            result.insert(0, node_id)
        
        for node_id in self.nodes.keys():
            if node_id not in visited:
                dfs(node_id)
        
        return result
    
    def get_executable_nodes(self, completed_nodes: Set[str]) -> List[str]:
        """Get nodes that are ready to execute."""
        executable = []
        
        for node_id in self.nodes.keys():
            if node_id in completed_nodes:
                continue
            
            # Check if all dependencies are completed
            dependencies = self.reverse_adjacency_list[node_id]
            if all(dep in completed_nodes for dep in dependencies):
                executable.append(node_id)
        
        return executable
    
    def validate_dag(self) -> bool:
        """Validate that the graph is a valid DAG."""
        try:
            self.topological_sort()
            return True
        except ValueError:
            return False


class WorkflowOrchestrator:
    """Main orchestrator for workflow execution."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def execute_flow(self, execution_id: str) -> None:
        """Execute a flow workflow."""
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
                
                # Execute workflow
                result = await self._execute_workflow(tasks, dag)
                
                # Update execution with results
                await self._complete_execution(db, execution_id, result)
                
            except Exception as e:
                self.logger.error("Workflow execution failed", execution_id=execution_id, error=str(e))
                await self._fail_execution(db, execution_id, str(e))
                raise
    
    def _create_tasks(self, nodes: List[FlowNode], edges: List[FlowEdge], flow_inputs: Dict[str, Any]) -> Dict[str, Task]:
        """Create executable tasks from flow nodes."""
        tasks = {}
        
        # Build dependency and handle mapping
        dependencies = {node.id: [] for node in nodes}
        input_mappings = {node.id: {} for node in nodes}
        
        for edge in edges:
            dependencies[edge.target].append(edge.source)
            # Map target handle to source node and handle
            target_handle = edge.target_handle or 'default'
            source_handle = edge.source_handle or 'default'
            input_mappings[edge.target][target_handle] = (edge.source, source_handle)
        
        for node in nodes:
            task = Task(
                id=f"task_{node.id}",
                node_id=node.id,
                node_type=node.type,
                config=node.data,
                inputs=flow_inputs if node.type == 'input' else {},
                dependencies=dependencies[node.id],
                input_mappings=input_mappings[node.id]
            )
            tasks[node.id] = task
        
        return tasks
    
    async def _execute_workflow(self, tasks: Dict[str, Task], dag: DAGAnalyzer) -> Dict[str, Any]:
        """Execute the workflow tasks in proper order."""
        completed_nodes = set()
        results = {}
        
        while len(completed_nodes) < len(tasks):
            # Get executable nodes
            executable_nodes = dag.get_executable_nodes(completed_nodes)
            
            if not executable_nodes:
                remaining = set(tasks.keys()) - completed_nodes
                raise ValueError(f"No executable nodes found. Remaining: {remaining}")
            
            # Execute nodes in parallel
            execution_tasks = []
            for node_id in executable_nodes:
                task = tasks[node_id]
                execution_tasks.append(self._execute_task(task, results))
            
            # Wait for all tasks to complete
            task_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Process results
            for i, node_id in enumerate(executable_nodes):
                task = tasks[node_id]
                result = task_results[i]
                
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    raise result
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    results[node_id] = result
                    completed_nodes.add(node_id)
        
        return results
    
    async def _execute_task(self, task: Task, context: Dict[str, Any]) -> Any:
        """Execute a single task using registered workers."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        self.logger.info("Executing task", task_id=task.id, node_type=task.node_type)
        
        try:
            # Import worker system
            from src.workers import node_registry, WorkerPool
            from src.workers.base_worker import ExecutionContext
            from src.workers.type_converter import TypeConverter
            
            # Prepare task inputs from dependencies using handle mappings
            task_inputs = task.inputs.copy() if task.inputs else {}
            
            # Use handle-based mapping for precise data routing
            for target_handle, (source_node, source_handle) in task.input_mappings.items():
                if source_node in context:
                    source_result = context[source_node]
                    # Handle different output formats
                    if isinstance(source_result, dict) and source_handle in source_result:
                        task_inputs[target_handle] = source_result[source_handle]
                    elif source_handle == 'default':
                        task_inputs[target_handle] = source_result
                    else:
                        self.logger.warning(
                            "Handle not found in source output",
                            source_node=source_node,
                            source_handle=source_handle
                        )
            
            # Get executor for node type
            executor = node_registry.get_executor(task.node_type)
            if not executor:
                raise ValueError(f"No executor found for node type: {task.node_type}")
            
            # Create execution context
            exec_context = ExecutionContext(
                execution_id="workflow",  # Could be enhanced to pass real execution ID
                flow_id="flow",
                node_id=task.node_id
            )
            
            # Execute using worker pool
            worker_pool = WorkerPool(max_workers=5)
            result = await worker_pool.execute_task(
                executor=executor,
                config=task.config,
                inputs=task_inputs,
                context=exec_context
            )
            
            task.completed_at = datetime.utcnow()
            return result
            
        except Exception as e:
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            self.logger.error("Task execution failed", task_id=task.id, error=str(e))
            raise
    
    
    async def _get_execution(self, db: AsyncSession, execution_id: str) -> Optional[Execution]:
        """Get execution from database."""
        from sqlalchemy import select
        result = await db.execute(select(Execution).where(Execution.id == execution_id))
        return result.scalar_one_or_none()
    
    async def _get_flow_version(self, db: AsyncSession, flow_id: str) -> Optional[FlowVersion]:
        """Get latest flow version."""
        from sqlalchemy import select
        result = await db.execute(
            select(FlowVersion)
            .where(FlowVersion.flow_id == flow_id)
            .order_by(FlowVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _update_execution_status(self, db: AsyncSession, execution_id: str, status: ExecutionStatus):
        """Update execution status."""
        result = await db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = status
            if status == ExecutionStatus.RUNNING and not execution.started_at:
                execution.started_at = datetime.utcnow()
            await db.commit()
    
    async def _complete_execution(self, db: AsyncSession, execution_id: str, results: Dict[str, Any]):
        """Complete execution with results."""
        result = await db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.outputs = results
            await db.commit()
    
    async def _fail_execution(self, db: AsyncSession, execution_id: str, error_message: str):
        """Fail execution with error."""
        result = await db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = error_message
            await db.commit()


# Global orchestrator instance
orchestrator = WorkflowOrchestrator()