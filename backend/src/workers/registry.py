"""
Worker Registry for managing node executors
"""

from typing import Dict, Optional, Type
from .base_worker import BaseWorker
import structlog

logger = structlog.get_logger(__name__)


class NodeRegistry:
    """Registry for node workers"""
    
    def __init__(self):
        self._workers: Dict[str, BaseWorker] = {}
        self.logger = logger
    
    def register(self, node_type: str, worker: BaseWorker) -> None:
        """Register a worker for a node type"""
        if node_type in self._workers:
            self.logger.warning(f"Overwriting existing worker for type: {node_type}")
        
        self._workers[node_type] = worker
        self.logger.info(f"Registered worker for node type: {node_type}")
    
    def unregister(self, node_type: str) -> None:
        """Unregister a worker"""
        if node_type in self._workers:
            del self._workers[node_type]
            self.logger.info(f"Unregistered worker for node type: {node_type}")
    
    def get_executor(self, node_type: str) -> Optional[BaseWorker]:
        """Get executor for a node type"""
        return self._workers.get(node_type)
    
    def list_registered(self) -> list[str]:
        """List all registered node types"""
        return list(self._workers.keys())