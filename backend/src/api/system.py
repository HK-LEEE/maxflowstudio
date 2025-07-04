"""
System management endpoints
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.database import get_db
from src.core.message_queue import message_queue
from src.middleware.auth import get_current_user
from src.config.settings import get_settings
from src.services.monitoring_service import monitoring_service

router = APIRouter()
settings = get_settings()


@router.get("/status")
async def system_status(
    db: AsyncSession = Depends(get_db),
    request: Request = None
) -> Dict[str, Any]:
    """Get system status information."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    try:
        # Database status
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Message queue status
    mq_status = "disconnected"
    queue_stats = {}
    if message_queue.connection and not message_queue.connection.is_closed:
        mq_status = "connected"
        queue_stats = await message_queue.get_queue_stats()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "url": str(settings.DATABASE_URL).split("@")[1] if "@" in str(settings.DATABASE_URL) else "hidden"
        },
        "message_queue": {
            "status": mq_status,
            "url": settings.RABBITMQ_URL.split("@")[1] if "@" in settings.RABBITMQ_URL else "hidden",
            "queues": queue_stats
        }
    }


@router.get("/queue-stats")
async def queue_statistics(request: Request = None) -> Dict[str, Any]:
    """Get message queue statistics."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    if not message_queue.connection or message_queue.connection.is_closed:
        return {"error": "Message queue not connected"}
    
    stats = await message_queue.get_queue_stats()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": stats
    }


@router.post("/queue/purge")
async def purge_queues(request: Request = None) -> Dict[str, Any]:
    """Purge all messages from queues (admin only)."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    if not message_queue.channel:
        return {"error": "Message queue not connected"}
    
    try:
        # Purge queues
        task_queue = await message_queue.channel.get_queue(message_queue.task_queue_name)
        result_queue = await message_queue.channel.get_queue(message_queue.result_queue_name)
        dlq = await message_queue.channel.get_queue(message_queue.dlq_name)
        
        task_purged = await task_queue.purge()
        result_purged = await result_queue.purge()
        dlq_purged = await dlq.purge()
        
        return {
            "success": True,
            "purged": {
                "task_queue": task_purged.message_count,
                "result_queue": result_purged.message_count,
                "dead_letter_queue": dlq_purged.message_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Failed to purge queues: {str(e)}"}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Comprehensive health check endpoint."""
    health_status = await monitoring_service.get_current_health()
    
    return {
        "status": health_status.status,
        "healthy": health_status.is_healthy,
        "services": health_status.services,
        "issues": health_status.issues,
        "timestamp": health_status.last_check.isoformat(),
        "uptime_seconds": health_status.metrics.uptime_seconds
    }


@router.get("/metrics")
async def get_metrics(
    hours: int = 24,
    request: Request = None
) -> Dict[str, Any]:
    """Get system metrics history."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    metrics_history = monitoring_service.get_metrics_history(hours)
    
    return {
        "period_hours": hours,
        "total_points": len(metrics_history),
        "metrics": metrics_history
    }


@router.get("/metrics/current")
async def get_current_metrics(
    request: Request = None
) -> Dict[str, Any]:
    """Get current system metrics."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    health_status = await monitoring_service.get_current_health()
    
    return {
        "timestamp": health_status.last_check.isoformat(),
        "system": {
            "cpu_percent": health_status.metrics.cpu_percent,
            "memory_percent": health_status.metrics.memory_percent,
            "memory_used_bytes": health_status.metrics.memory_used,
            "memory_total_bytes": health_status.metrics.memory_total,
            "disk_percent": health_status.metrics.disk_percent,
            "disk_used_bytes": health_status.metrics.disk_used,
            "disk_total_bytes": health_status.metrics.disk_total,
            "active_connections": health_status.metrics.active_connections,
            "uptime_seconds": health_status.metrics.uptime_seconds
        },
        "application": {
            "total_flows": health_status.app_metrics.total_flows,
            "active_flows": health_status.app_metrics.active_flows,
            "total_executions": health_status.app_metrics.total_executions,
            "running_executions": health_status.app_metrics.running_executions,
            "completed_executions": health_status.app_metrics.completed_executions,
            "failed_executions": health_status.app_metrics.failed_executions,
            "total_deployments": health_status.app_metrics.total_deployments,
            "active_deployments": health_status.app_metrics.active_deployments,
            "queue_size": health_status.app_metrics.queue_size,
            "worker_count": health_status.app_metrics.worker_count
        }
    }


@router.post("/monitoring/start")
async def start_monitoring(
    request: Request = None
) -> Dict[str, str]:
    """Start system monitoring."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    await monitoring_service.start_monitoring()
    return {"message": "Monitoring started"}


@router.post("/monitoring/stop")
async def stop_monitoring(
    request: Request = None
) -> Dict[str, str]:
    """Stop system monitoring."""
    current_user = get_current_user(request)
    if not current_user or not current_user.get("is_superuser", False):
        return {"error": "Admin access required"}
    
    await monitoring_service.stop_monitoring()
    return {"message": "Monitoring stopped"}


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Detailed health check including all system components."""
    health_status = await monitoring_service.get_current_health()
    system_info = monitoring_service.get_system_info()
    db_stats = await monitoring_service.get_database_stats()
    
    return {
        "status": health_status.status,
        "healthy": health_status.is_healthy,
        "version": "1.0.0",
        "services": health_status.services,
        "system": {
            "cpu_percent": health_status.metrics.cpu_percent,
            "memory_percent": health_status.metrics.memory_percent,
            "disk_percent": health_status.metrics.disk_percent,
            "uptime_seconds": health_status.metrics.uptime_seconds,
            "active_connections": health_status.metrics.active_connections
        },
        "application": {
            "total_flows": health_status.app_metrics.total_flows,
            "total_executions": health_status.app_metrics.total_executions,
            "running_executions": health_status.app_metrics.running_executions,
            "total_deployments": health_status.app_metrics.total_deployments,
            "active_deployments": health_status.app_metrics.active_deployments,
            "queue_size": health_status.app_metrics.queue_size
        },
        "database": db_stats,
        "system_info": system_info,
        "last_check": health_status.last_check.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }