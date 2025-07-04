"""
Graph Scheduler and Dependency Management
Flow: Dependency analysis → Topological sorting → Execution scheduling → Parallel coordination
"""

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import structlog

from .graph_execution_state import NodeExecutionStatus

logger = structlog.get_logger()


class CyclicDependencyError(Exception):
    """Raised when a cyclic dependency is detected in the graph."""
    pass


class GraphNode:
    """
    Represents a node in the execution graph.
    
    Node Structure:
    - id: Unique identifier
    - component_type: Type of component to execute
    - config: Component configuration
    - inputs: Input connection mappings
    - dependencies: Other nodes this node depends on
    - dependents: Other nodes that depend on this node
    """
    
    def __init__(self, node_id: str, component_type: str, config: Dict[str, Any] = None):
        self.id = node_id
        self.component_type = component_type
        self.config = config or {}
        self.inputs: Dict[str, Tuple[str, str]] = {}  # {input_name: (source_node_id, output_name)}
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
        self.status = NodeExecutionStatus.PENDING
    
    def add_input_connection(self, input_name: str, source_node_id: str, output_name: str) -> None:
        """Add an input connection from another node."""
        self.inputs[input_name] = (source_node_id, output_name)
        self.dependencies.add(source_node_id)
    
    def __repr__(self) -> str:
        return f"GraphNode(id={self.id}, type={self.component_type}, deps={self.dependencies})"


class GraphScheduler:
    """
    Schedules and manages execution order of graph nodes.
    
    Scheduler Process:
    1. build_dependency_graph() → Analyze node connections and dependencies
    2. validate_graph() → Check for cycles and missing dependencies
    3. topological_sort() → Calculate execution order
    4. schedule_execution() → Determine parallel execution groups
    5. track_progress() → Monitor execution state and readiness
    
    Responsibilities:
    - Dependency graph construction and validation
    - Topological sorting for execution order
    - Parallel execution scheduling
    - Node readiness detection
    - Progress tracking and state management
    """
    
    def __init__(self):
        """Initialize graph scheduler."""
        self.nodes: Dict[str, GraphNode] = {}
        self.logger = logger.bind(component="graph_scheduler")
    
    def add_node(self, node_id: str, component_type: str, config: Dict[str, Any] = None) -> None:
        """Add a node to the graph."""
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")
        
        self.nodes[node_id] = GraphNode(node_id, component_type, config)
        self.logger.debug("Node added to graph", node_id=node_id, component_type=component_type)
    
    def add_edge(self, source_node_id: str, output_name: str, target_node_id: str, input_name: str) -> None:
        """Add an edge (connection) between two nodes."""
        if source_node_id not in self.nodes:
            raise ValueError(f"Source node {source_node_id} not found")
        if target_node_id not in self.nodes:
            raise ValueError(f"Target node {target_node_id} not found")
        
        # Add connection to target node
        target_node = self.nodes[target_node_id]
        target_node.add_input_connection(input_name, source_node_id, output_name)
        
        # Add dependent relationship to source node
        source_node = self.nodes[source_node_id]
        source_node.dependents.add(target_node_id)
        
        self.logger.debug(
            "Edge added to graph",
            source=source_node_id,
            target=target_node_id,
            output=output_name,
            input=input_name
        )
    
    def validate_graph(self) -> None:
        """Validate the graph for cycles and missing dependencies."""
        # Check for cyclic dependencies
        if self._has_cycles():
            raise CyclicDependencyError("Graph contains cyclic dependencies")
        
        # Validate all dependencies exist
        for node in self.nodes.values():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    raise ValueError(f"Node {node.id} depends on non-existent node {dep_id}")
        
        self.logger.info("Graph validation completed", node_count=len(self.nodes))
    
    def _has_cycles(self) -> bool:
        """Check if the graph has cyclic dependencies using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dep_id in self.nodes[node_id].dependencies:
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def topological_sort(self) -> List[str]:
        """
        Return nodes in topological order using Kahn's algorithm.
        
        Returns:
            List of node IDs in execution order
        """
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node in self.nodes.values():
            for dep_id in node.dependencies:
                in_degree[node.id] += 1
        
        # Initialize queue with nodes having no dependencies
        queue = deque([node_id for node_id in self.nodes if in_degree[node_id] == 0])
        sorted_nodes = []
        
        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)
            
            # Update in-degrees of dependent nodes
            for dependent_id in self.nodes[node_id].dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        if len(sorted_nodes) != len(self.nodes):
            raise CyclicDependencyError("Graph contains cycles")
        
        self.logger.info("Topological sort completed", order=sorted_nodes)
        return sorted_nodes
    
    def get_execution_groups(self) -> List[List[str]]:
        """
        Group nodes that can be executed in parallel.
        
        Returns:
            List of groups, where each group contains nodes that can run in parallel
        """
        groups = []
        remaining_nodes = set(self.nodes.keys())
        
        while remaining_nodes:
            # Find nodes with no unsatisfied dependencies
            ready_nodes = []
            for node_id in remaining_nodes:
                node = self.nodes[node_id]
                unsatisfied_deps = node.dependencies.intersection(remaining_nodes)
                if not unsatisfied_deps:
                    ready_nodes.append(node_id)
            
            if not ready_nodes:
                # Should not happen if graph is acyclic
                raise CyclicDependencyError("No ready nodes found - possible cycle")
            
            groups.append(ready_nodes)
            remaining_nodes -= set(ready_nodes)
        
        self.logger.info("Execution groups created", group_count=len(groups))
        return groups
    
    def get_ready_nodes(self, completed_nodes: Set[str]) -> List[str]:
        """
        Get nodes that are ready to execute based on completed dependencies.
        
        Args:
            completed_nodes: Set of node IDs that have completed execution
            
        Returns:
            List of node IDs ready for execution
        """
        ready_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status in [NodeExecutionStatus.COMPLETED, NodeExecutionStatus.RUNNING]:
                continue
            
            # Check if all dependencies are satisfied
            if node.dependencies.issubset(completed_nodes):
                ready_nodes.append(node_id)
        
        return ready_nodes
    
    def update_node_status(self, node_id: str, status: NodeExecutionStatus) -> None:
        """Update the execution status of a node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        self.nodes[node_id].status = status
        self.logger.debug("Node status updated", node_id=node_id, status=status.value)
    
    def get_node_dependencies(self, node_id: str) -> Set[str]:
        """Get the dependencies of a specific node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        return self.nodes[node_id].dependencies.copy()
    
    def get_node_dependents(self, node_id: str) -> Set[str]:
        """Get the nodes that depend on a specific node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        return self.nodes[node_id].dependents.copy()
    
    def get_node_inputs(self, node_id: str) -> Dict[str, Tuple[str, str]]:
        """Get the input connections for a specific node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        return self.nodes[node_id].inputs.copy()
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph structure."""
        total_nodes = len(self.nodes)
        total_edges = sum(len(node.dependencies) for node in self.nodes.values())
        
        # Calculate depth (longest path)
        try:
            sorted_nodes = self.topological_sort()
            max_depth = self._calculate_max_depth(sorted_nodes)
        except CyclicDependencyError:
            max_depth = -1  # Indicates cycle
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "max_depth": max_depth,
            "has_cycles": max_depth == -1,
            "average_dependencies": total_edges / total_nodes if total_nodes > 0 else 0
        }
    
    def _calculate_max_depth(self, sorted_nodes: List[str]) -> int:
        """Calculate the maximum depth of the graph."""
        depths = {}
        
        for node_id in sorted_nodes:
            node = self.nodes[node_id]
            if not node.dependencies:
                depths[node_id] = 0
            else:
                depths[node_id] = max(depths[dep_id] for dep_id in node.dependencies) + 1
        
        return max(depths.values()) if depths else 0