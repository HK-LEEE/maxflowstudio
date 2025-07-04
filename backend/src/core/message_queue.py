"""
Message Queue System using RabbitMQ
Flow: Producer -> Exchange -> Queue -> Consumer -> Task Execution
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

import aio_pika
from aio_pika import Message, ExchangeType
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class TaskMessage:
    """Message format for task execution."""
    task_id: str
    execution_id: str
    flow_id: str
    node_id: str
    node_type: str
    config: Dict[str, Any]
    inputs: Dict[str, Any]
    dependencies: list[str]
    created_at: str
    retry_count: int = 0
    max_retries: int = 3


class MessageQueue:
    """RabbitMQ message queue manager."""
    
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.logger = structlog.get_logger(__name__)
        
        # Queue names
        self.task_queue_name = "flowstudio.tasks"
        self.result_queue_name = "flowstudio.results"
        self.dlq_name = "flowstudio.tasks.dlq"  # Dead Letter Queue
        
        # Consumer callback
        self.task_consumer_callback: Optional[Callable] = None
    
    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Create exchange
            self.exchange = await self.channel.declare_exchange(
                "flowstudio",
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Create queues
            await self._create_queues()
            
            self.logger.info("Connected to RabbitMQ", url=settings.RABBITMQ_URL)
            
        except Exception as e:
            self.logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    async def _create_queues(self) -> None:
        """Create necessary queues."""
        if not self.channel or not self.exchange:
            raise RuntimeError("Channel or exchange not initialized")
        
        # Dead Letter Queue
        dlq = await self.channel.declare_queue(
            self.dlq_name,
            durable=True,
            arguments={}
        )
        
        # Main task queue with DLQ
        task_queue = await self.channel.declare_queue(
            self.task_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "flowstudio",
                "x-dead-letter-routing-key": "tasks.failed",
                "x-message-ttl": 3600000,  # 1 hour TTL
            }
        )
        
        # Result queue
        result_queue = await self.channel.declare_queue(
            self.result_queue_name,
            durable=True
        )
        
        # Bind queues to exchange
        await task_queue.bind(self.exchange, "tasks.execute")
        await result_queue.bind(self.exchange, "tasks.result")
        await dlq.bind(self.exchange, "tasks.failed")
        
        self.logger.info("Queues created and bound")
    
    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.logger.info("Disconnected from RabbitMQ")
    
    async def publish_task(self, task_message: TaskMessage) -> None:
        """Publish a task to the queue."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
        
        message_body = json.dumps(asdict(task_message))
        message = Message(
            message_body.encode(),
            content_type="application/json",
            headers={
                "task_id": task_message.task_id,
                "execution_id": task_message.execution_id,
                "node_type": task_message.node_type,
                "retry_count": task_message.retry_count,
            },
            message_id=task_message.task_id,
            timestamp=datetime.utcnow(),
        )
        
        await self.exchange.publish(
            message,
            routing_key="tasks.execute"
        )
        
        self.logger.info(
            "Task published to queue",
            task_id=task_message.task_id,
            node_type=task_message.node_type
        )
    
    async def publish_result(self, task_id: str, execution_id: str, 
                           result: Dict[str, Any], success: bool = True) -> None:
        """Publish task result."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
        
        result_message = {
            "task_id": task_id,
            "execution_id": execution_id,
            "result": result,
            "success": success,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        message = Message(
            json.dumps(result_message).encode(),
            content_type="application/json",
            headers={"task_id": task_id, "execution_id": execution_id},
        )
        
        await self.exchange.publish(
            message,
            routing_key="tasks.result"
        )
        
        self.logger.info(
            "Result published",
            task_id=task_id,
            success=success
        )
    
    async def start_task_consumer(self, callback: Callable[[TaskMessage], Any]) -> None:
        """Start consuming tasks from the queue."""
        if not self.channel:
            raise RuntimeError("Channel not initialized")
        
        self.task_consumer_callback = callback
        
        task_queue = await self.channel.get_queue(self.task_queue_name)
        
        async def process_message(message: aio_pika.IncomingMessage) -> None:
            async with message.process():
                try:
                    # Parse message
                    task_data = json.loads(message.body.decode())
                    task_message = TaskMessage(**task_data)
                    
                    self.logger.info(
                        "Processing task",
                        task_id=task_message.task_id,
                        node_type=task_message.node_type
                    )
                    
                    # Execute callback
                    await callback(task_message)
                    
                except json.JSONDecodeError as e:
                    self.logger.error("Failed to decode message", error=str(e))
                    # Message will be rejected and sent to DLQ
                    raise
                    
                except Exception as e:
                    self.logger.error(
                        "Task processing failed",
                        task_id=task_data.get("task_id", "unknown"),
                        error=str(e)
                    )
                    
                    # Check retry count
                    retry_count = task_data.get("retry_count", 0)
                    max_retries = task_data.get("max_retries", 3)
                    
                    if retry_count < max_retries:
                        # Retry the task
                        task_data["retry_count"] = retry_count + 1
                        await self._retry_task(TaskMessage(**task_data))
                    else:
                        # Send to DLQ
                        self.logger.error(
                            "Task failed after max retries",
                            task_id=task_data.get("task_id"),
                            retry_count=retry_count
                        )
                    raise
        
        await task_queue.consume(process_message)
        self.logger.info("Task consumer started")
    
    async def _retry_task(self, task_message: TaskMessage) -> None:
        """Retry a failed task with exponential backoff."""
        # Wait before retrying (exponential backoff)
        delay = min(2 ** task_message.retry_count, 60)  # Max 60 seconds
        await asyncio.sleep(delay)
        
        await self.publish_task(task_message)
        
        self.logger.info(
            "Task retried",
            task_id=task_message.task_id,
            retry_count=task_message.retry_count,
            delay=delay
        )
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        if not self.channel:
            return {}
        
        try:
            task_queue = await self.channel.get_queue(self.task_queue_name)
            result_queue = await self.channel.get_queue(self.result_queue_name)
            dlq = await self.channel.get_queue(self.dlq_name)
            
            return {
                "task_queue": {
                    "name": self.task_queue_name,
                    "message_count": task_queue.declaration_result.message_count,
                    "consumer_count": task_queue.declaration_result.consumer_count,
                },
                "result_queue": {
                    "name": self.result_queue_name,
                    "message_count": result_queue.declaration_result.message_count,
                    "consumer_count": result_queue.declaration_result.consumer_count,
                },
                "dead_letter_queue": {
                    "name": self.dlq_name,
                    "message_count": dlq.declaration_result.message_count,
                    "consumer_count": dlq.declaration_result.consumer_count,
                }
            }
        except Exception as e:
            self.logger.error("Failed to get queue stats", error=str(e))
            return {}


class QueuedTaskExecutor:
    """Task executor that uses message queue."""
    
    def __init__(self, message_queue: MessageQueue):
        self.mq = message_queue
        self.logger = structlog.get_logger(__name__)
    
    async def execute_task_from_queue(self, task_message: TaskMessage) -> None:
        """Execute a task received from the queue."""
        from src.workers import node_registry, WorkerPool
        from src.workers.base_worker import ExecutionContext
        
        try:
            # Get executor for node type
            executor = node_registry.get_executor(task_message.node_type)
            if not executor:
                raise ValueError(f"No executor found for node type: {task_message.node_type}")
            
            # Create execution context
            context = ExecutionContext(
                execution_id=task_message.execution_id,
                flow_id=task_message.flow_id,
                node_id=task_message.node_id
            )
            
            # Execute task
            worker_pool = WorkerPool(max_workers=5)
            result = await worker_pool.execute_task(
                executor=executor,
                config=task_message.config,
                inputs=task_message.inputs,
                context=context
            )
            
            # Publish result
            await self.mq.publish_result(
                task_id=task_message.task_id,
                execution_id=task_message.execution_id,
                result=result,
                success=True
            )
            
        except Exception as e:
            self.logger.error(
                "Task execution failed",
                task_id=task_message.task_id,
                error=str(e)
            )
            
            # Publish error result
            await self.mq.publish_result(
                task_id=task_message.task_id,
                execution_id=task_message.execution_id,
                result={"error": str(e)},
                success=False
            )
            raise


# Global message queue instance
message_queue = MessageQueue()