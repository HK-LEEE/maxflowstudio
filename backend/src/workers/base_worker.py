"""
Base Worker class for all node executors
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExecutionContext:
    """Context information for node execution"""
    execution_id: str
    flow_id: str
    node_id: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseWorker(ABC):
    """Abstract base class for all node workers"""
    
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute the node logic
        
        Args:
            config: Node configuration from flow designer
            inputs: Input data from connected nodes (keyed by handle name)
            context: Execution context information
            
        Returns:
            Dictionary of outputs keyed by handle name
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any], required: list[str]) -> None:
        """Validate that required inputs are present"""
        missing = [key for key in required if key not in inputs or inputs[key] is None]
        if missing:
            raise ValueError(f"Missing required inputs: {missing}")
    
    def format_output(self, **kwargs) -> Dict[str, Any]:
        """Format output with handle names"""
        return kwargs
    
    async def cleanup(self) -> None:
        """Cleanup resources after execution"""
        pass