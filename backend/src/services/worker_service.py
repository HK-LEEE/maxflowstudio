"""
Worker Service - Independent worker process for executing tasks
Flow: Start Service -> Connect to Queue -> Process Tasks -> Send Results
"""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from src.core.message_queue import MessageQueue, QueuedTaskExecutor
from src.workers import initialize_workers
from src.config.settings import get_settings
from src.core.logging import setup_logging

logger = structlog.get_logger(__name__)


class WorkerService:
    """Independent worker service for processing tasks."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.executor: Optional[QueuedTaskExecutor] = None
        self.running = False
        self.logger = structlog.get_logger(__name__)
    
    async def start(self) -> None:
        """Start the worker service."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("Starting Worker Service")
            
            # Initialize workers
            initialize_workers()
            self.logger.info("Node executors initialized")
            
            # Connect to message queue
            await self.message_queue.connect()
            self.logger.info("Connected to message queue")
            
            # Create task executor
            self.executor = QueuedTaskExecutor(self.message_queue)
            
            # Start consuming tasks
            await self.message_queue.start_task_consumer(
                self.executor.execute_task_from_queue
            )
            
            self.running = True
            self.logger.info("Worker service started successfully")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error("Failed to start worker service", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the worker service."""
        self.logger.info("Stopping worker service")
        self.running = False
        
        if self.message_queue:
            await self.message_queue.disconnect()
        
        self.logger.info("Worker service stopped")
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for worker service."""
    service = WorkerService()
    service.setup_signal_handlers()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()
    except Exception as e:
        logger.error("Worker service failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())