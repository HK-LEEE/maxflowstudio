"""
Monitoring Service - System monitoring and health checks
Flow: Health checks -> Metrics collection -> Alerting -> Logging
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from src.models.execution import Execution, ExecutionStatus
from src.models.flow import Flow
from src.models.api_deployment import ApiDeployment, DeploymentStatus
from src.core.database import AsyncSessionLocal
from src.core.message_queue import message_queue

logger = structlog.get_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int
    active_connections: int
    uptime_seconds: float


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    timestamp: datetime
    total_flows: int
    active_flows: int
    total_executions: int
    running_executions: int
    completed_executions: int
    failed_executions: int
    total_deployments: int
    active_deployments: int
    queue_size: int
    worker_count: int


@dataclass
class HealthStatus:
    """System health status."""
    is_healthy: bool
    status: str  # healthy, degraded, unhealthy
    services: Dict[str, bool]
    metrics: SystemMetrics
    app_metrics: ApplicationMetrics
    issues: List[str]
    last_check: datetime


class MonitoringService:
    """Service for system monitoring and health checks."""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.health_checks: Dict[str, Any] = {}
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'failed_execution_rate': 10.0,  # % of executions failing
            'response_time': 5.0,  # seconds
        }
        self.monitoring_enabled = True
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self.monitoring_enabled = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring service started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self.monitoring_enabled = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Collect metrics
                system_metrics = await self.collect_system_metrics()
                app_metrics = await self.collect_application_metrics()
                
                # Store metrics
                self.metrics_history.append({
                    'timestamp': datetime.utcnow(),
                    'system': system_metrics,
                    'application': app_metrics
                })
                
                # Check health
                health_status = await self.check_health()
                
                # Log alerts if needed
                await self._check_alerts(health_status)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network connections (approximate)
        connections = len(psutil.net_connections())
        
        # Uptime
        uptime = time.time() - self.start_time
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_total=memory.total,
            disk_percent=disk.percent,
            disk_used=disk.used,
            disk_total=disk.total,
            active_connections=connections,
            uptime_seconds=uptime
        )
    
    async def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics."""
        
        async with AsyncSessionLocal() as db:
            # Flow metrics
            total_flows_result = await db.execute(select(func.count(Flow.id)))
            total_flows = total_flows_result.scalar() or 0
            
            # Execution metrics
            total_executions_result = await db.execute(select(func.count(Execution.id)))
            total_executions = total_executions_result.scalar() or 0
            
            running_executions_result = await db.execute(
                select(func.count(Execution.id)).where(
                    Execution.status == ExecutionStatus.RUNNING
                )
            )
            running_executions = running_executions_result.scalar() or 0
            
            completed_executions_result = await db.execute(
                select(func.count(Execution.id)).where(
                    Execution.status == ExecutionStatus.COMPLETED
                )
            )
            completed_executions = completed_executions_result.scalar() or 0
            
            failed_executions_result = await db.execute(
                select(func.count(Execution.id)).where(
                    Execution.status == ExecutionStatus.FAILED
                )
            )
            failed_executions = failed_executions_result.scalar() or 0
            
            # Deployment metrics
            total_deployments_result = await db.execute(select(func.count(ApiDeployment.id)))
            total_deployments = total_deployments_result.scalar() or 0
            
            active_deployments_result = await db.execute(
                select(func.count(ApiDeployment.id)).where(
                    ApiDeployment.status == DeploymentStatus.ACTIVE
                )
            )
            active_deployments = active_deployments_result.scalar() or 0
            
            # Queue metrics (if available)
            queue_size = 0
            if hasattr(message_queue, 'is_connected') and message_queue.is_connected:
                try:
                    queue_info = await message_queue.get_queue_info()
                    queue_size = queue_info.get('message_count', 0)
                except Exception:
                    pass
        
        return ApplicationMetrics(
            timestamp=datetime.utcnow(),
            total_flows=total_flows,
            active_flows=total_flows,  # Assuming all flows are active
            total_executions=total_executions,
            running_executions=running_executions,
            completed_executions=completed_executions,
            failed_executions=failed_executions,
            total_deployments=total_deployments,
            active_deployments=active_deployments,
            queue_size=queue_size,
            worker_count=1  # Basic worker count
        )
    
    async def check_health(self) -> HealthStatus:
        """Perform comprehensive health check."""
        
        issues = []
        services = {}
        
        # Check database connectivity
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
                services['database'] = True
        except Exception as e:
            services['database'] = False
            issues.append(f"Database connection failed: {str(e)}")
        
        # Check message queue (optional)
        services['message_queue'] = getattr(message_queue, 'is_connected', False)
        if not getattr(message_queue, 'is_connected', False):
            issues.append("Message queue not connected (optional)")
        
        # Check system resources
        system_metrics = await self.collect_system_metrics()
        services['system_resources'] = True
        
        if system_metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            issues.append(f"High CPU usage: {system_metrics.cpu_percent:.1f}%")
            services['system_resources'] = False
        
        if system_metrics.memory_percent > self.alert_thresholds['memory_percent']:
            issues.append(f"High memory usage: {system_metrics.memory_percent:.1f}%")
            services['system_resources'] = False
        
        if system_metrics.disk_percent > self.alert_thresholds['disk_percent']:
            issues.append(f"High disk usage: {system_metrics.disk_percent:.1f}%")
            services['system_resources'] = False
        
        # Check application health
        app_metrics = await self.collect_application_metrics()
        services['application'] = True
        
        if app_metrics.total_executions > 0:
            failure_rate = (app_metrics.failed_executions / app_metrics.total_executions) * 100
            if failure_rate > self.alert_thresholds['failed_execution_rate']:
                issues.append(f"High execution failure rate: {failure_rate:.1f}%")
                services['application'] = False
        
        # Determine overall health status
        critical_services = ['database', 'system_resources', 'application']
        critical_healthy = all(services.get(service, False) for service in critical_services)
        
        if critical_healthy and not issues:
            status = "healthy"
            is_healthy = True
        elif critical_healthy:
            status = "degraded"
            is_healthy = True
        else:
            status = "unhealthy"
            is_healthy = False
        
        return HealthStatus(
            is_healthy=is_healthy,
            status=status,
            services=services,
            metrics=system_metrics,
            app_metrics=app_metrics,
            issues=issues,
            last_check=datetime.utcnow()
        )
    
    async def _check_alerts(self, health_status: HealthStatus) -> None:
        """Check for alert conditions and log them."""
        
        if not health_status.is_healthy:
            logger.warning(
                "System health degraded",
                status=health_status.status,
                issues=health_status.issues,
                services=health_status.services
            )
        
        # Log high resource usage
        metrics = health_status.metrics
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            logger.warning("High CPU usage detected", cpu_percent=metrics.cpu_percent)
        
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            logger.warning("High memory usage detected", memory_percent=metrics.memory_percent)
        
        if metrics.disk_percent > self.alert_thresholds['disk_percent']:
            logger.warning("High disk usage detected", disk_percent=metrics.disk_percent)
    
    async def get_current_health(self) -> HealthStatus:
        """Get current system health status."""
        return await self.check_health()
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for the specified number of hours."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_metrics = [
            metric for metric in self.metrics_history
            if metric['timestamp'] >= cutoff_time
        ]
        
        return filtered_metrics
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        
        return {
            'platform': psutil.platform,
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': psutil.disk_usage('/').total,
            'uptime_seconds': time.time() - self.start_time,
            'python_version': psutil.process_iter(),
            'monitoring_enabled': self.monitoring_enabled,
            'metrics_count': len(self.metrics_history)
        }
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        
        try:
            async with AsyncSessionLocal() as db:
                # Basic table counts
                flows_count = await db.execute(select(func.count(Flow.id)))
                executions_count = await db.execute(select(func.count(Execution.id)))
                deployments_count = await db.execute(select(func.count(ApiDeployment.id)))
                
                # Recent activity (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_executions = await db.execute(
                    select(func.count(Execution.id)).where(
                        Execution.created_at >= yesterday
                    )
                )
                
                return {
                    'total_flows': flows_count.scalar() or 0,
                    'total_executions': executions_count.scalar() or 0,
                    'total_deployments': deployments_count.scalar() or 0,
                    'recent_executions_24h': recent_executions.scalar() or 0,
                    'connection_status': 'healthy'
                }
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            return {
                'connection_status': 'error',
                'error': str(e)
            }


# Global monitoring service instance
monitoring_service = MonitoringService()