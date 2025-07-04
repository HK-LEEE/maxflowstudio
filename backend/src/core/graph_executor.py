"""
Graph Execution Engine - Refactored (559 → 400 lines)
Flow: Flow definition → Graph building → Validation → Execution → Result collection
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import structlog
from pydantic import BaseModel, Field

from .component_base import BaseComponent, ComponentResult, ComponentStatus
from .component_registry import registry
from .graph_execution_state import (
    GraphExecutionContext, 
    ExecutionStatus, 
    NodeExecutionStatus
)
from .graph_scheduler import GraphScheduler, CyclicDependencyError

logger = structlog.get_logger()


class FlowDefinition(BaseModel):
    """
    Flow definition for graph execution.
    
    Flow Structure:
    - nodes: List of component nodes with configuration
    - edges: List of connections between nodes
    - metadata: Flow information and settings
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Flow name")
    description: Optional[str] = Field(None, description="Flow description")
    nodes: List[Dict[str, Any]] = Field(..., description="Node definitions")
    edges: List[Dict[str, Any]] = Field(..., description="Edge connections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GraphExecutor:
    """
    Main graph execution engine using modular scheduler and state management.
    
    Executor Process:
    1. parse_flow() → Convert flow definition to internal graph structure
    2. build_graph() → Use scheduler to create dependency graph
    3. validate_execution() → Check graph validity and component availability
    4. execute_flow() → Orchestrate parallel execution using state manager
    5. collect_results() → Aggregate and format execution results
    
    Responsibilities:
    - Flow definition parsing and validation
    - Component instantiation and lifecycle management
    - Execution coordination and monitoring
    - Error handling and recovery
    - Result aggregation and reporting
    """
    
    def __init__(self, max_concurrent_nodes: int = 5):
        """Initialize graph executor."""
        self.max_concurrent_nodes = max_concurrent_nodes
        self.logger = logger.bind(component="graph_executor")
        
        # Execution tracking
        self.active_executions: Dict[str, GraphExecutionContext] = {}
        
        # Component instances cache
        self._component_cache: Dict[str, BaseComponent] = {}
    
    async def execute_flow(self, flow_definition: FlowDefinition) -> GraphExecutionContext:
        """
        Execute a complete flow definition.
        
        Args:
            flow_definition: The flow to execute
            
        Returns:
            GraphExecutionContext with execution results
        """
        # Create execution context
        context = GraphExecutionContext(flow_id=flow_definition.id)
        self.active_executions[context.execution_id] = context
        
        try:
            context.start_execution()
            
            # Build execution graph
            scheduler = await self._build_execution_graph(flow_definition, context)
            
            # Validate graph
            scheduler.validate_graph()
            
            # Execute nodes
            await self._execute_graph(scheduler, context)
            
            # Check final status
            if context.status == ExecutionStatus.RUNNING:
                context.complete_execution()
                
        except Exception as e:
            context.fail_execution(str(e))
            self.logger.error("Flow execution failed", 
                            flow_id=flow_definition.id, 
                            error=str(e))
        finally:
            # Cleanup
            await self._cleanup_execution(context)
            if context.execution_id in self.active_executions:
                del self.active_executions[context.execution_id]
        
        return context
    
    async def _build_execution_graph(
        self, 
        flow_definition: FlowDefinition, 
        context: GraphExecutionContext
    ) -> GraphScheduler:
        """Build the execution graph from flow definition."""
        scheduler = GraphScheduler()
        
        # Add nodes to scheduler
        for node_def in flow_definition.nodes:
            node_id = node_def["id"]
            component_type = node_def["type"]
            config = node_def.get("data", {}).get("config", {})
            
            scheduler.add_node(node_id, component_type, config)
            
            # Validate component exists
            component_class = registry.get_component_class(component_type)
            if not component_class:
                raise ValueError(f"Component type '{component_type}' not found")
        
        # Add edges to scheduler
        for edge_def in flow_definition.edges:
            source_id = edge_def["source"]
            target_id = edge_def["target"]
            source_handle = edge_def.get("sourceHandle", "output")
            target_handle = edge_def.get("targetHandle", "input")
            
            scheduler.add_edge(source_id, source_handle, target_id, target_handle)
        
        self.logger.info("Execution graph built", 
                        node_count=len(flow_definition.nodes),
                        edge_count=len(flow_definition.edges))
        
        return scheduler
    
    async def _execute_graph(self, scheduler: GraphScheduler, context: GraphExecutionContext) -> None:
        """Execute the graph using parallel node execution."""
        completed_nodes: Set[str] = set()
        semaphore = asyncio.Semaphore(self.max_concurrent_nodes)
        
        while len(completed_nodes) < len(scheduler.nodes):
            # Get nodes ready for execution
            ready_nodes = scheduler.get_ready_nodes(completed_nodes)
            
            if not ready_nodes:
                # Check if we're waiting for running nodes
                running_nodes = [
                    node_id for node_id, node in scheduler.nodes.items()
                    if node.status == NodeExecutionStatus.RUNNING
                ]
                
                if not running_nodes:
                    # No ready nodes and no running nodes - likely an error
                    remaining_nodes = set(scheduler.nodes.keys()) - completed_nodes
                    context.fail_execution(f"Execution stuck - remaining nodes: {remaining_nodes}")
                    break
                
                # Wait a bit for running nodes to complete
                await asyncio.sleep(0.1)
                continue
            
            # Execute ready nodes in parallel
            tasks = []
            for node_id in ready_nodes:
                if scheduler.nodes[node_id].status == NodeExecutionStatus.PENDING:
                    task = asyncio.create_task(
                        self._execute_node_with_semaphore(semaphore, scheduler, node_id, context)
                    )
                    tasks.append((node_id, task))
            
            # Wait for at least one task to complete
            if tasks:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Update completed nodes
                for node_id, task in tasks:
                    if task in done:
                        try:
                            await task  # Ensure any exceptions are raised
                            if scheduler.nodes[node_id].status == NodeExecutionStatus.COMPLETED:
                                completed_nodes.add(node_id)
                        except Exception as e:
                            self.logger.error("Node execution failed", node_id=node_id, error=str(e))
                            context.fail_node_execution(node_id, str(e))
                            scheduler.update_node_status(node_id, NodeExecutionStatus.FAILED)
        
        self.logger.info("Graph execution completed", 
                        completed_count=len(completed_nodes),
                        total_count=len(scheduler.nodes))
    
    async def _execute_node_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore,
        scheduler: GraphScheduler, 
        node_id: str, 
        context: GraphExecutionContext
    ) -> None:
        """Execute a single node with concurrency control."""
        async with semaphore:
            await self._execute_single_node(scheduler, node_id, context)
    
    async def _execute_single_node(
        self, 
        scheduler: GraphScheduler, 
        node_id: str, 
        context: GraphExecutionContext
    ) -> None:
        """Execute a single node."""
        node = scheduler.nodes[node_id]
        
        try:
            # Update status
            scheduler.update_node_status(node_id, NodeExecutionStatus.RUNNING)
            context.start_node_execution(node_id, node.component_type)
            
            # Create component instance
            component = await self._create_component_instance(node.component_type, node.config)
            
            # Set input values from connected nodes
            await self._set_node_inputs(component, scheduler, node_id, context)
            
            # Initialize and execute component
            await component.initialize()
            await component.build_results()
            
            # Get outputs
            outputs = {}
            for output_def in component.outputs:
                value = component.get_output_value(output_def.name)
                if value is not None:
                    outputs[output_def.name] = value
            
            # Complete node execution
            component_result = ComponentResult(
                component_id=component.id,
                status=component.status,
                outputs=outputs,
                execution_time=getattr(component, '_execution_time', 0.0),
                error_message=getattr(component, '_error_message', None)
            )
            
            context.complete_node_execution(node_id, outputs, component_result)
            scheduler.update_node_status(node_id, NodeExecutionStatus.COMPLETED)
            
            # Cleanup component
            await component.cleanup()
            
        except Exception as e:
            error_msg = f"Node execution failed: {str(e)}"
            context.fail_node_execution(node_id, error_msg)
            scheduler.update_node_status(node_id, NodeExecutionStatus.FAILED)
            raise
    
    async def _create_component_instance(self, component_type: str, config: Dict[str, Any]) -> BaseComponent:
        """Create and configure a component instance."""
        component_class = registry.get_component_class(component_type)
        if not component_class:
            raise ValueError(f"Component type '{component_type}' not found")
        
        # Create instance with configuration
        instance = component_class(**config)
        return instance
    
    async def _set_node_inputs(
        self, 
        component: BaseComponent, 
        scheduler: GraphScheduler, 
        node_id: str, 
        context: GraphExecutionContext
    ) -> None:
        """Set input values for a node from connected source nodes."""
        node = scheduler.nodes[node_id]
        
        for input_name, (source_node_id, output_name) in node.inputs.items():
            # Get output value from source node
            source_outputs = context.get_node_outputs(source_node_id)
            if output_name in source_outputs:
                value = source_outputs[output_name]
                component.set_input_value(input_name, value)
                self.logger.debug("Input value set", 
                                node_id=node_id,
                                input_name=input_name,
                                source_node=source_node_id,
                                output_name=output_name)
    
    async def _cleanup_execution(self, context: GraphExecutionContext) -> None:
        """Cleanup resources after execution."""
        # Clear component cache for this execution
        # (In a more advanced implementation, this would be more sophisticated)
        self._component_cache.clear()
        
        self.logger.info("Execution cleanup completed", 
                        execution_id=context.execution_id)
    
    def get_execution_status(self, execution_id: str) -> Optional[GraphExecutionContext]:
        """Get the status of a running execution."""
        return self.active_executions.get(execution_id)
    
    def get_active_executions(self) -> List[str]:
        """Get list of active execution IDs."""
        return list(self.active_executions.keys())
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if execution_id not in self.active_executions:
            return False
        
        context = self.active_executions[execution_id]
        context.cancel_execution()
        
        # In a full implementation, you would also cancel running tasks
        self.logger.info("Execution cancelled", execution_id=execution_id)
        return True