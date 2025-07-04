"""
Worker Pool for managing concurrent task execution
"""

import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from .base_worker import BaseWorker, ExecutionContext
import structlog

logger = structlog.get_logger(__name__)


class WorkerPool:
    """Pool for managing worker execution"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logger
        self._semaphore = asyncio.Semaphore(max_workers)
    
    async def execute_task(
        self,
        executor: BaseWorker,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Execute a task using the worker pool"""
        async with self._semaphore:
            try:
                self.logger.info(
                    "Executing task",
                    node_id=context.node_id,
                    executor_class=executor.__class__.__name__
                )
                
                # Execute the worker
                result = await executor.execute(config, inputs, context)
                
                self.logger.info(
                    "Task completed successfully",
                    node_id=context.node_id,
                    has_result=result is not None
                )
                
                return result
                
            except Exception as e:
                self.logger.error(
                    "Task execution failed",
                    node_id=context.node_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
            finally:
                # Cleanup
                await executor.cleanup()
    
    def shutdown(self):
        """Shutdown the worker pool"""
        self.executor.shutdown(wait=True)
        self.logger.info("Worker pool shut down")