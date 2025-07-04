"""
Deployment Service - Manages API deployment lifecycle
Flow: Create deployment -> Generate dynamic endpoint -> Route requests -> Track usage
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import Request, HTTPException, status

from src.models.api_deployment import ApiDeployment, DeploymentStatus
from src.models.flow import Flow, FlowVersion
from src.models.execution import Execution, ExecutionStatus
from src.core.workflow_engine import WorkflowOrchestrator
from src.core.queued_workflow_engine import queued_orchestrator

logger = structlog.get_logger(__name__)


class DeploymentService:
    """Service for managing API deployments."""
    
    def __init__(self):
        self.active_deployments: Dict[str, ApiDeployment] = {}
        self.request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.orchestrator = WorkflowOrchestrator()
    
    async def deploy_api(self, deployment_id: str, db: AsyncSession) -> None:
        """Deploy a flow as an API endpoint."""
        
        # Get deployment
        query = select(ApiDeployment).where(ApiDeployment.id == deployment_id)
        result = await db.execute(query)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        # Get flow and validate
        flow_query = select(Flow).where(Flow.id == deployment.flow_id)
        flow_result = await db.execute(flow_query)
        flow = flow_result.scalar_one_or_none()
        
        if not flow:
            raise ValueError(f"Flow {deployment.flow_id} not found")
        
        # Get latest flow version
        version_query = select(FlowVersion).where(
            FlowVersion.flow_id == deployment.flow_id
        ).order_by(FlowVersion.created_at.desc())
        version_result = await db.execute(version_query)
        flow_version = version_result.first()
        
        if not flow_version or not flow_version[0].definition:
            raise ValueError(f"Flow definition not found for deployment {deployment_id}")
        
        # Validate flow definition
        flow_def = flow_version[0].definition
        if not self._validate_flow_for_deployment(flow_def):
            raise ValueError("Flow is not valid for API deployment")
        
        # Generate input/output schemas if not provided
        if not deployment.input_schema:
            deployment.input_schema = self._generate_input_schema(flow_def)
        
        if not deployment.output_schema:
            deployment.output_schema = self._generate_output_schema(flow_def)
        
        # Update deployment status
        deployment.status = DeploymentStatus.ACTIVE
        deployment.deployed_at = datetime.utcnow()
        deployment.error_message = None
        
        await db.commit()
        
        # Add to active deployments
        self.active_deployments[deployment.endpoint_path] = deployment
        
        logger.info(
            "API deployed successfully",
            deployment_id=deployment_id,
            endpoint_path=deployment.endpoint_path,
            flow_id=deployment.flow_id
        )
    
    async def activate_deployment(self, deployment_id: str, db: AsyncSession) -> None:
        """Activate an existing deployment."""
        
        query = select(ApiDeployment).where(ApiDeployment.id == deployment_id)
        result = await db.execute(query)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        deployment.status = DeploymentStatus.ACTIVE
        deployment.deployed_at = datetime.utcnow()
        deployment.error_message = None
        
        await db.commit()
        
        # Add to active deployments
        self.active_deployments[deployment.endpoint_path] = deployment
        
        logger.info("Deployment activated", deployment_id=deployment_id)
    
    async def deactivate_deployment(self, deployment_id: str, db: AsyncSession) -> None:
        """Deactivate a deployment."""
        
        query = select(ApiDeployment).where(ApiDeployment.id == deployment_id)
        result = await db.execute(query)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        deployment.status = DeploymentStatus.INACTIVE
        await db.commit()
        
        # Remove from active deployments
        if deployment.endpoint_path in self.active_deployments:
            del self.active_deployments[deployment.endpoint_path]
        
        logger.info("Deployment deactivated", deployment_id=deployment_id)
    
    async def delete_deployment(self, deployment_id: str, db: AsyncSession) -> None:
        """Delete a deployment."""
        
        query = select(ApiDeployment).where(ApiDeployment.id == deployment_id)
        result = await db.execute(query)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        # Remove from active deployments
        if deployment.endpoint_path in self.active_deployments:
            del self.active_deployments[deployment.endpoint_path]
        
        # Delete from database
        await db.delete(deployment)
        await db.commit()
        
        logger.info("Deployment deleted", deployment_id=deployment_id)
    
    async def execute_deployed_flow(
        self,
        endpoint_path: str,
        request_data: Dict[str, Any],
        request: Request,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute a deployed flow via API."""
        
        # Get deployment
        deployment = self.active_deployments.get(endpoint_path)
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API endpoint not found"
            )
        
        if deployment.status != DeploymentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API endpoint is not active"
            )
        
        # Rate limiting
        if deployment.rate_limit:
            client_ip = request.client.host
            current_minute = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            
            if self.request_counts[endpoint_path][current_minute] >= deployment.rate_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
        
        # Validate input
        if deployment.input_schema:
            try:
                self._validate_input(request_data, deployment.input_schema)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid input: {str(e)}"
                )
        
        try:
            # Create execution
            import uuid
            execution = Execution(
                id=str(uuid.uuid4()),
                flow_id=deployment.flow_id,
                user_id=deployment.user_id,
                inputs=request_data,
                status=ExecutionStatus.PENDING
            )
            
            db.add(execution)
            await db.commit()
            await db.refresh(execution)
            
            # Execute flow
            if queued_orchestrator and hasattr(queued_orchestrator.mq, 'is_connected') and queued_orchestrator.mq.is_connected:
                await queued_orchestrator.execute_flow(execution.id)
            else:
                await self.orchestrator.execute_flow(execution.id)
            
            # Wait for completion (with timeout)
            result = await self._wait_for_execution_completion(execution.id, db)
            
            # Update usage statistics
            await self._update_usage_stats(deployment.id, db)
            
            # Update request count for rate limiting
            if deployment.rate_limit:
                current_minute = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                self.request_counts[endpoint_path][current_minute] += 1
            
            return result
            
        except Exception as e:
            logger.error(
                "Deployed flow execution failed",
                deployment_id=deployment.id,
                endpoint_path=endpoint_path,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Flow execution failed: {str(e)}"
            )
    
    async def load_active_deployments(self, db: AsyncSession) -> None:
        """Load active deployments from database."""
        
        query = select(ApiDeployment).where(
            ApiDeployment.status == DeploymentStatus.ACTIVE
        )
        result = await db.execute(query)
        deployments = result.scalars().all()
        
        for deployment in deployments:
            self.active_deployments[deployment.endpoint_path] = deployment
        
        logger.info(f"Loaded {len(deployments)} active deployments")
    
    def _validate_flow_for_deployment(self, flow_def: Dict[str, Any]) -> bool:
        """Validate that a flow is suitable for API deployment."""
        
        nodes = flow_def.get('nodes', [])
        
        # Must have at least one input and one output node
        # Check data.type instead of direct type for FlowStudio node structure
        input_nodes = [n for n in nodes if n.get('data', {}).get('type') == 'input']
        output_nodes = [n for n in nodes if n.get('data', {}).get('type') == 'output']
        
        logger.info(f"Flow validation: found {len(input_nodes)} input nodes, {len(output_nodes)} output nodes")
        
        if not input_nodes:
            logger.warning("Flow has no input nodes")
            return False
        
        if not output_nodes:
            logger.warning("Flow has no output nodes")
            return False
        
        logger.info("Flow validation passed")
        return True
    
    def _generate_input_schema(self, flow_def: Dict[str, Any]) -> Dict[str, Any]:
        """Generate input schema from flow definition."""
        
        nodes = flow_def.get('nodes', [])
        input_nodes = [n for n in nodes if n.get('data', {}).get('type') == 'input']
        
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for node in input_nodes:
            node_data = node.get('data', {})
            field_name = node_data.get('name', f"input_{node['id']}")
            field_type = node_data.get('dataType', 'string')
            
            schema["properties"][field_name] = {
                "type": field_type,
                "description": node_data.get('description', '')
            }
            
            if node_data.get('required', False):
                schema["required"].append(field_name)
        
        return schema
    
    def _generate_output_schema(self, flow_def: Dict[str, Any]) -> Dict[str, Any]:
        """Generate output schema from flow definition."""
        
        nodes = flow_def.get('nodes', [])
        output_nodes = [n for n in nodes if n.get('data', {}).get('type') == 'output']
        
        schema = {
            "type": "object",
            "properties": {}
        }
        
        for node in output_nodes:
            node_data = node.get('data', {})
            field_name = node_data.get('name', f"output_{node['id']}")
            field_type = node_data.get('dataType', 'string')
            
            schema["properties"][field_name] = {
                "type": field_type,
                "description": node_data.get('description', '')
            }
        
        return schema
    
    def _validate_input(self, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate input data against schema."""
        
        required_fields = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' is missing")
        
        # Check field types
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get('type', 'string')
                if not self._check_type(value, expected_type):
                    raise ValueError(f"Field '{field}' must be of type {expected_type}")
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True
    
    async def _wait_for_execution_completion(
        self,
        execution_id: str,
        db: AsyncSession,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Wait for execution to complete and return results."""
        
        import asyncio
        
        start_time = datetime.utcnow()
        
        while True:
            # Check execution status
            query = select(Execution).where(Execution.id == execution_id)
            result = await db.execute(query)
            execution = result.scalar_one_or_none()
            
            if not execution:
                raise ValueError(f"Execution {execution_id} not found")
            
            if execution.status == ExecutionStatus.COMPLETED:
                return execution.results or {}
            
            if execution.status == ExecutionStatus.FAILED:
                raise ValueError(f"Execution failed: {execution.error_message}")
            
            # Check timeout
            if (datetime.utcnow() - start_time).total_seconds() > timeout_seconds:
                raise ValueError("Execution timeout")
            
            # Wait before checking again
            await asyncio.sleep(1)
    
    async def _update_usage_stats(self, deployment_id: str, db: AsyncSession) -> None:
        """Update deployment usage statistics."""
        
        now = datetime.utcnow()
        
        await db.execute(
            update(ApiDeployment)
            .where(ApiDeployment.id == deployment_id)
            .values(
                total_requests=ApiDeployment.total_requests + 1,
                last_request_at=now
            )
        )
        await db.commit()


# Global deployment service instance
deployment_service = DeploymentService()