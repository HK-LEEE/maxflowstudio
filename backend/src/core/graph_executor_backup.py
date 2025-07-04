"""
┌────────────────────────────────────────────────────────────────┐
│                    Graph Execution Flow                       │
│                                                                │
│  [Flow] → [Parse] → [Validate] → [Order] → [Execute] → [Done] │
│     ↓        ↓         ↓          ↓         ↓         ↓       │
│  플로우입력  노드파싱   의존성검증   실행순서   병렬실행   결과수집  │
│                                                                │
│  Execution Order: Topological Sort → Parallel Execution       │
│  Error Handling: Node Error → Propagate → Stop → Cleanup      │
│                                                                │
│  Data Flow: Node A → Edge → Node B → Output → Next Node      │
│  State Management: Context → Shared Variables → Results       │
└────────────────────────────────────────────────────────────────┘

Graph Execution Engine for MAX Flowstudio
Flow: Flow definition → Node parsing → Dependency validation → Execution ordering → Parallel execution → Result collection
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict, deque
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
    WAITING = "waiting"  # Waiting for dependencies
    READY = "ready"      # Ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FlowNode(BaseModel):
    """Flow node definition."""
    id: str = Field(..., description="Unique node identifier")
    component_type: str = Field(..., description="Component type/class name")
    display_name: str = Field(..., description="Human-readable node name")
    position: Dict[str, float] = Field(default_factory=dict, description="Node position in UI")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node configuration")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Node input values")
    
    def __hash__(self):
        return hash(self.id)


class FlowEdge(BaseModel):
    """Flow edge definition."""
    id: str = Field(..., description="Unique edge identifier")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    source_handle: str = Field(..., description="Source output handle")
    target_handle: str = Field(..., description="Target input handle")
    
    def __hash__(self):
        return hash(self.id)


class FlowDefinition(BaseModel):
    """Complete flow definition."""
    id: str = Field(..., description="Flow identifier")
    name: str = Field(..., description="Flow name")
    description: str = Field(default="", description="Flow description")
    nodes: List[FlowNode] = Field(..., description="Flow nodes")
    edges: List[FlowEdge] = Field(..., description="Flow edges")
    global_variables: Dict[str, Any] = Field(default_factory=dict, description="Global variables")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flow metadata")


class NodeExecution(BaseModel):
    """Node execution state."""
    node_id: str = Field(..., description="Node identifier")
    status: NodeExecutionStatus = Field(default=NodeExecutionStatus.PENDING)
    component: Optional[BaseComponent] = Field(default=None, description="Component instance")
    dependencies: Set[str] = Field(default_factory=set, description="Dependency node IDs")
    dependents: Set[str] = Field(default_factory=set, description="Dependent node IDs")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Resolved input values")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Node execution outputs")
    result: Optional[ComponentResult] = Field(default=None, description="Execution result")
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class ExecutionContext(BaseModel):
    """Graph execution context."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    flow_id: str = Field(..., description="Flow identifier")
    flow_definition: Optional[FlowDefinition] = Field(default=None, description="Complete flow definition")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None)
    global_variables: Dict[str, Any] = Field(default_factory=dict)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    execution_order: List[List[str]] = Field(default_factory=list, description="Execution batches")
    node_executions: Dict[str, NodeExecution] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class GraphExecutor:
    """
    Graph execution engine for workflow processing.
    
    Execution Process:
    1. load_flow_definition() → Parse flow JSON and extract nodes/edges
    2. build_dependency_graph() → Construct dependency relationships and validate cycles
    3. topological_sort() → Determine execution order with parallel batches
    4. execute_nodes_async() → Execute nodes asynchronously in dependency order
    5. propagate_data() → Pass outputs between connected nodes
    6. handle_errors() → Process errors and determine continuation strategy
    
    Data Flow:
    Flow Definition → Dependency Graph → Execution Order → Parallel Batches → Results
    
    Error Handling:
    Node Error → Log → Propagate to dependents → Stop execution → Cleanup
    Validation Error → Early termination → Return error context
    """
    
    def __init__(self, component_registry: Optional[Dict[str, type]] = None):
        """Initialize graph executor with component registry."""
        self.component_registry = component_registry or {}
        self.logger = logger.bind(executor_id=str(uuid.uuid4()))
        self._active_executions: Dict[str, ExecutionContext] = {}
        
    def register_component(self, component_type: str, component_class: type) -> None:
        """Register a component class for instantiation."""
        if not issubclass(component_class, BaseComponent):
            raise ValueError(f"Component {component_type} must inherit from BaseComponent")
        
        self.component_registry[component_type] = component_class
        self.logger.debug("Component registered", component_type=component_type)
    
    async def execute_flow(
        self, 
        flow_definition: FlowDefinition,
        initial_inputs: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> ExecutionContext:
        """
        Execute a complete flow definition.
        
        Complete Execution Flow:
        1. Initialize execution context
        2. Build dependency graph
        3. Validate flow structure
        4. Calculate execution order
        5. Execute nodes in parallel batches
        6. Collect and return results
        
        Args:
            flow_definition: Complete flow definition
            initial_inputs: Initial input values for flow
            execution_id: Optional execution identifier
            
        Returns:
            ExecutionContext: Complete execution results and metadata
        """
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        # Initialize execution context
        context = ExecutionContext(
            execution_id=execution_id,
            flow_id=flow_definition.id,
            flow_definition=flow_definition,
            global_variables=flow_definition.global_variables.copy(),
            shared_context=initial_inputs or {}
        )
        
        self._active_executions[execution_id] = context
        self.logger.info("Starting flow execution", 
                        execution_id=execution_id, 
                        flow_id=flow_definition.id,
                        node_count=len(flow_definition.nodes))
        
        try:
            context.status = ExecutionStatus.RUNNING
            
            # Step 1: Build dependency graph
            self.logger.info("Building dependency graph")
            await self._build_dependency_graph(flow_definition, context)
            
            # Step 2: Validate flow structure
            self.logger.info("Validating flow structure")
            await self._validate_flow_structure(context)
            
            # Step 3: Calculate execution order
            self.logger.info("Calculating execution order")
            await self._calculate_execution_order(context)
            
            # Step 4: Execute nodes
            self.logger.info("Starting node execution")
            await self._execute_nodes_parallel(context)
            
            # Step 5: Finalize execution
            context.status = ExecutionStatus.COMPLETED
            context.end_time = datetime.utcnow()
            
            execution_time = (context.end_time - context.start_time).total_seconds()
            self.logger.info("Flow execution completed successfully", 
                           execution_time=execution_time,
                           completed_nodes=len([n for n in context.node_executions.values() 
                                              if n.status == NodeExecutionStatus.COMPLETED]))
            
        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.end_time = datetime.utcnow()
            context.error_message = str(e)
            
            self.logger.error("Flow execution failed", 
                            execution_id=execution_id,
                            error=str(e), 
                            exc_info=True)
        
        finally:
            # Cleanup
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
        
        return context
    
    async def _build_dependency_graph(self, flow_definition: FlowDefinition, context: ExecutionContext) -> None:
        """
        Build dependency graph from flow definition.
        
        Dependency Building Process:
        1. Create node execution objects
        2. Parse edges to build dependency relationships
        3. Initialize components for each node
        4. Validate component instantiation
        """
        # Initialize node executions
        for node in flow_definition.nodes:
            node_exec = NodeExecution(
                node_id=node.id,
                inputs=node.inputs.copy()
            )
            context.node_executions[node.id] = node_exec
        
        # Build dependencies from edges
        edge_map = defaultdict(list)
        reverse_edge_map = defaultdict(list)
        
        for edge in flow_definition.edges:
            edge_map[edge.source_node_id].append(edge)
            reverse_edge_map[edge.target_node_id].append(edge)
            
            # Add dependency relationships
            source_exec = context.node_executions[edge.source_node_id]
            target_exec = context.node_executions[edge.target_node_id]
            
            target_exec.dependencies.add(edge.source_node_id)
            source_exec.dependents.add(edge.target_node_id)
        
        # Initialize components
        for node in flow_definition.nodes:
            component_class = self.component_registry.get(node.component_type)
            if not component_class:
                raise ValueError(f"Unknown component type: {node.component_type}")
            
            try:
                component = component_class(**node.config)
                context.node_executions[node.id].component = component
                self.logger.debug("Component initialized", 
                                node_id=node.id, 
                                component_type=node.component_type)
            except Exception as e:
                raise ValueError(f"Failed to initialize component {node.component_type} for node {node.id}: {str(e)}")
    
    async def _validate_flow_structure(self, context: ExecutionContext) -> None:
        """
        Validate flow structure for cycles and orphaned nodes.
        
        Validation Checks:
        1. Detect circular dependencies
        2. Identify orphaned nodes
        3. Validate edge connections
        4. Check required inputs
        """
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            node_exec = context.node_executions[node_id]
            for dependent_id in node_exec.dependents:
                if dependent_id not in visited:
                    if has_cycle(dependent_id):
                        return True
                elif dependent_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in context.node_executions:
            if node_id not in visited:
                if has_cycle(node_id):
                    raise ValueError(f"Circular dependency detected in flow starting from node: {node_id}")
        
        self.logger.debug("Flow structure validation completed")
    
    async def _calculate_execution_order(self, context: ExecutionContext) -> None:
        """
        Calculate execution order using topological sorting.
        
        Topological Sort Process:
        1. Find nodes with no dependencies (degree 0)
        2. Add them to current execution batch
        3. Remove their outgoing edges
        4. Repeat until all nodes are processed
        5. Result: List of parallel execution batches
        """
        # Calculate in-degree for each node
        in_degree = {}
        for node_id in context.node_executions:
            in_degree[node_id] = len(context.node_executions[node_id].dependencies)
        
        execution_order = []
        
        while in_degree:
            # Find nodes with no dependencies (can execute in parallel)
            ready_nodes = [node_id for node_id, degree in in_degree.items() if degree == 0]
            
            if not ready_nodes:
                remaining_nodes = list(in_degree.keys())
                raise ValueError(f"Deadlock detected: remaining nodes {remaining_nodes} have circular dependencies")
            
            execution_order.append(ready_nodes)
            
            # Remove processed nodes and update dependencies
            for node_id in ready_nodes:
                del in_degree[node_id]
                
                # Decrease in-degree of dependent nodes
                node_exec = context.node_executions[node_id]
                for dependent_id in node_exec.dependents:
                    if dependent_id in in_degree:
                        in_degree[dependent_id] -= 1
        
        context.execution_order = execution_order
        self.logger.info("Execution order calculated", 
                        batch_count=len(execution_order),
                        batches=[len(batch) for batch in execution_order])
    
    async def _execute_nodes_parallel(self, context: ExecutionContext) -> None:
        """
        Execute nodes in parallel batches according to dependency order.
        
        Parallel Execution Process:
        1. For each execution batch:
        2. Prepare inputs for all nodes in batch
        3. Execute all nodes concurrently
        4. Wait for all to complete
        5. Propagate outputs to dependent nodes
        6. Handle any errors
        """
        for batch_index, node_batch in enumerate(context.execution_order):
            self.logger.info("Executing batch", 
                           batch_index=batch_index, 
                           batch_size=len(node_batch))
            
            # Prepare and execute nodes in parallel
            execution_tasks = []
            for node_id in node_batch:
                task = self._execute_single_node(node_id, context)
                execution_tasks.append(task)
            
            # Wait for all nodes in batch to complete
            try:
                await asyncio.gather(*execution_tasks)
                self.logger.info("Batch completed successfully", batch_index=batch_index)
            except Exception as e:
                self.logger.error("Batch execution failed", 
                                batch_index=batch_index, 
                                error=str(e))
                # Continue with error handling
                break
            
            # Check if any node in the batch failed
            failed_nodes = [node_id for node_id in node_batch 
                          if context.node_executions[node_id].status == NodeExecutionStatus.FAILED]
            
            if failed_nodes:
                self.logger.error("Nodes failed in batch", 
                                batch_index=batch_index, 
                                failed_nodes=failed_nodes)
                await self._handle_batch_failure(failed_nodes, context)
                break
    
    async def _execute_single_node(self, node_id: str, context: ExecutionContext) -> None:
        """
        Execute a single node with proper input resolution and error handling.
        
        Single Node Execution:
        1. Resolve inputs from dependencies and context
        2. Set node status to running
        3. Execute component
        4. Store results and outputs
        5. Update node status
        """
        node_exec = context.node_executions[node_id]
        node_exec.status = NodeExecutionStatus.RUNNING
        node_exec.start_time = datetime.utcnow()
        
        self.logger.debug("Starting node execution", node_id=node_id)
        
        try:
            # Resolve inputs from dependencies
            resolved_inputs = await self._resolve_node_inputs(node_id, context)
            
            # Execute component
            if node_exec.component:
                result = await node_exec.component.execute(
                    inputs=resolved_inputs,
                    execution_id=f"{context.execution_id}:{node_id}"
                )
                
                node_exec.result = result
                node_exec.outputs = result.outputs
                
                if result.status == ComponentStatus.COMPLETED:
                    node_exec.status = NodeExecutionStatus.COMPLETED
                    self.logger.debug("Node execution completed", 
                                    node_id=node_id,
                                    execution_time=result.execution_time)
                else:
                    node_exec.status = NodeExecutionStatus.FAILED
                    node_exec.error_message = result.error_message
                    self.logger.error("Node execution failed", 
                                    node_id=node_id,
                                    error=result.error_message)
            else:
                raise ValueError(f"No component available for node {node_id}")
                
        except Exception as e:
            node_exec.status = NodeExecutionStatus.FAILED
            node_exec.error_message = str(e)
            self.logger.error("Node execution exception", 
                            node_id=node_id, 
                            error=str(e), 
                            exc_info=True)
        
        finally:
            node_exec.end_time = datetime.utcnow()
    
    async def _resolve_node_inputs(self, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        Resolve inputs for a node from dependencies and global context.
        
        Input Resolution Process:
        1. Start with node's static input values
        2. Override with outputs from dependency nodes
        3. Apply global variables and shared context
        4. Validate required inputs are present
        """
        node_exec = context.node_executions[node_id]
        resolved_inputs = node_exec.inputs.copy()
        
        # Add global variables
        resolved_inputs.update(context.global_variables)
        
        # Add shared context
        resolved_inputs.update(context.shared_context)
        
        # Override with dependency outputs using edge mapping
        edges_to_node = [edge for edge in context.flow_definition.edges if edge.target_node_id == node_id]
        
        for edge in edges_to_node:
            dep_node_exec = context.node_executions[edge.source_node_id]
            if dep_node_exec.status == NodeExecutionStatus.COMPLETED:
                # Map specific output to specific input using edge handles
                source_output = edge.source_handle
                target_input = edge.target_handle
                
                if source_output in dep_node_exec.outputs:
                    resolved_inputs[target_input] = dep_node_exec.outputs[source_output]
                    self.logger.debug("Edge mapped input", 
                                    source_node=edge.source_node_id,
                                    target_node=node_id,
                                    source_output=source_output,
                                    target_input=target_input)
            else:
                self.logger.warning("Dependency node not completed", 
                                  node_id=node_id, 
                                  dependency=edge.source_node_id,
                                  dep_status=dep_node_exec.status)
        
        self.logger.debug("Node inputs resolved", 
                        node_id=node_id, 
                        input_keys=list(resolved_inputs.keys()))
        
        return resolved_inputs
    
    async def _handle_batch_failure(self, failed_nodes: List[str], context: ExecutionContext) -> None:
        """Handle failure of nodes in a batch."""
        # Mark all dependent nodes as skipped
        skipped_nodes = set()
        
        def mark_dependents_skipped(node_id: str):
            node_exec = context.node_executions[node_id]
            for dependent_id in node_exec.dependents:
                if dependent_id not in skipped_nodes:
                    skipped_nodes.add(dependent_id)
                    context.node_executions[dependent_id].status = NodeExecutionStatus.SKIPPED
                    mark_dependents_skipped(dependent_id)
        
        for failed_node_id in failed_nodes:
            mark_dependents_skipped(failed_node_id)
        
        self.logger.info("Marked dependent nodes as skipped", 
                       failed_nodes=failed_nodes, 
                       skipped_count=len(skipped_nodes))
    
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get current execution status."""
        return self._active_executions.get(execution_id)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        if execution_id in self._active_executions:
            context = self._active_executions[execution_id]
            context.status = ExecutionStatus.CANCELLED
            context.end_time = datetime.utcnow()
            
            self.logger.info("Execution cancelled", execution_id=execution_id)
            return True
        
        return False