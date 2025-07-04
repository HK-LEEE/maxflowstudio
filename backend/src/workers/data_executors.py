"""
Data Node Executors
Flow: Data Config -> External System -> Data Processing
"""

import asyncio
import json
from typing import Dict, Any, Optional

import httpx
import structlog

from .base_worker import BaseNodeExecutor

logger = structlog.get_logger(__name__)


class InputExecutor(BaseNodeExecutor):
    """Executor for input nodes."""
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute input node - simply pass through the inputs."""
        return inputs or {}


class OutputExecutor(BaseNodeExecutor):
    """Executor for output nodes."""
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute output node - format and return final results."""
        output_format = config.get('output_format', 'json')
        
        if output_format == 'json':
            return {
                'final_output': inputs,
                'format': 'json',
                'timestamp': asyncio.get_event_loop().time()
            }
        elif output_format == 'text':
            # Convert inputs to text format
            text_output = self._convert_to_text(inputs)
            return {
                'final_output': text_output,
                'format': 'text',
                'timestamp': asyncio.get_event_loop().time()
            }
        else:
            return inputs
    
    def _convert_to_text(self, inputs: Dict[str, Any]) -> str:
        """Convert inputs to text format."""
        text_parts = []
        for key, value in inputs.items():
            if isinstance(value, dict):
                text_parts.append(f"{key}: {json.dumps(value, indent=2)}")
            else:
                text_parts.append(f"{key}: {value}")
        return "\n".join(text_parts)


class ApiExecutor(BaseNodeExecutor):
    """Executor for API call nodes."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate API configuration."""
        required_fields = ['url', 'method']
        return all(field in config for field in required_fields)
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP API call."""
        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = self._parse_headers(config.get('headers', '{}'))
        body = config.get('body', '')
        timeout = float(config.get('timeout', 30))
        
        # Replace placeholders in URL and body with input values
        formatted_url = self._format_string(url, inputs)
        formatted_body = self._format_string(body, inputs) if body else None
        
        try:
            async with httpx.AsyncClient() as client:
                request_kwargs = {
                    'url': formatted_url,
                    'headers': headers,
                    'timeout': timeout
                }
                
                if method in ['POST', 'PUT', 'PATCH'] and formatted_body:
                    # Try to parse as JSON, fallback to text
                    try:
                        request_kwargs['json'] = json.loads(formatted_body)
                    except json.JSONDecodeError:
                        request_kwargs['data'] = formatted_body
                
                response = await client.request(method, **request_kwargs)
                
                # Try to parse response as JSON
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text
                
                return {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'url': formatted_url,
                    'method': method,
                    'success': 200 <= response.status_code < 300
                }
                
        except Exception as e:
            self.logger.error("API call failed", url=formatted_url, error=str(e))
            return {
                'error': str(e),
                'url': formatted_url,
                'method': method,
                'success': False
            }
    
    def _parse_headers(self, headers_str: str) -> Dict[str, str]:
        """Parse headers from string format."""
        try:
            return json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError:
            return {}
    
    def _format_string(self, template: str, inputs: Dict[str, Any]) -> str:
        """Format string with input values."""
        formatted = template
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            formatted = formatted.replace(placeholder, str(value))
        return formatted


class DatabaseExecutor(BaseNodeExecutor):
    """Executor for database operation nodes."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate database configuration."""
        operation = config.get('operation')
        return operation in ['select', 'insert', 'update', 'delete']
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operation."""
        operation = config.get('operation', 'select')
        table = config.get('table', '')
        query = config.get('query', '')
        
        # For security and demo purposes, simulate database operations
        return await self._simulate_database_operation(operation, table, query, inputs)
    
    async def _simulate_database_operation(self, operation: str, table: str, 
                                         query: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate database operation for demo purposes."""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        if operation == 'select':
            # Simulate SELECT results
            return {
                'operation': 'select',
                'table': table,
                'rows_returned': 5,
                'data': [
                    {'id': 1, 'name': 'Sample Record 1', 'value': 100},
                    {'id': 2, 'name': 'Sample Record 2', 'value': 200},
                    {'id': 3, 'name': 'Sample Record 3', 'value': 300},
                ],
                'query': query,
                'simulated': True
            }
        elif operation == 'insert':
            # Simulate INSERT
            return {
                'operation': 'insert',
                'table': table,
                'rows_affected': 1,
                'inserted_id': 42,
                'inputs': inputs,
                'simulated': True
            }
        elif operation == 'update':
            # Simulate UPDATE
            return {
                'operation': 'update',
                'table': table,
                'rows_affected': 3,
                'inputs': inputs,
                'simulated': True
            }
        elif operation == 'delete':
            # Simulate DELETE
            return {
                'operation': 'delete',
                'table': table,
                'rows_affected': 2,
                'simulated': True
            }
        else:
            return {
                'error': f'Unsupported operation: {operation}',
                'simulated': True
            }