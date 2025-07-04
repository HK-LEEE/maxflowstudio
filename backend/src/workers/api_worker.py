"""
API Node Worker - Enhanced with authentication and advanced features
"""

import json
import aiohttp
import asyncio
import base64
from typing import Dict, Any, Optional
from .base_worker import BaseWorker, ExecutionContext


class ApiWorker(BaseWorker):
    """Worker for API call nodes"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Make HTTP API calls with enhanced authentication and features
        """
        self.logger.info("Executing API node", node_id=context.node_id)
        
        # Get configuration
        method = config.get('method', 'GET').upper()
        url = config.get('url', '')
        headers = config.get('headers', {})
        timeout = config.get('timeout', 30)
        retry_count = config.get('retry_count', 0)
        retry_delay = config.get('retry_delay', 1)
        
        # Authentication configuration
        auth_type = config.get('auth_type', 'none')  # none, bearer, basic, api_key
        auth_config = config.get('auth_config', {})
        
        # Get input values
        body = inputs.get('body')
        query_params = inputs.get('params', {})
        
        if not url:
            raise ValueError("API URL is required")
        
        # Prepare headers
        headers = self._prepare_headers(headers, auth_type, auth_config)
        
        # Add query parameters to URL if provided
        if query_params and isinstance(query_params, dict):
            import urllib.parse
            query_string = urllib.parse.urlencode(query_params)
            url = f"{url}{'&' if '?' in url else '?'}{query_string}"
        
        # Parse body if it's a string and method requires body
        if body and isinstance(body, str) and method in ['POST', 'PUT', 'PATCH']:
            try:
                body = json.loads(body)
            except:
                # Keep as string if not valid JSON
                pass
        
        # Execute with retry logic
        for attempt in range(retry_count + 1):
            try:
                result = await self._make_request(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout=timeout,
                    context=context
                )
                
                # If successful, return result
                if result.get('status', 0) < 500:  # Don't retry on client errors
                    return result
                    
            except aiohttp.ClientError as e:
                if attempt == retry_count:  # Last attempt
                    self.logger.error(
                        "API request failed after retries",
                        node_id=context.node_id,
                        error=str(e),
                        attempts=attempt + 1
                    )
                    return self.format_output(
                        response=None,
                        status=0,
                        error=str(e),
                        attempts=attempt + 1
                    )
                else:
                    self.logger.warning(
                        "API request failed, retrying",
                        node_id=context.node_id,
                        error=str(e),
                        attempt=attempt + 1,
                        retry_delay=retry_delay
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    
            except Exception as e:
                self.logger.error(
                    "Unexpected error in API call",
                    node_id=context.node_id,
                    error=str(e),
                    attempt=attempt + 1
                )
                if attempt == retry_count:
                    raise
                await asyncio.sleep(retry_delay)
    
    def _prepare_headers(self, headers: Dict[str, Any], auth_type: str, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare headers including authentication"""
        
        # Parse headers if they're a string
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except:
                headers = {}
        
        # Ensure headers is a dictionary
        if not isinstance(headers, dict):
            headers = {}
        
        # Add authentication headers
        if auth_type == 'bearer':
            token = auth_config.get('token', '')
            if token:
                headers['Authorization'] = f'Bearer {token}'
                
        elif auth_type == 'basic':
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            if username and password:
                credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'
                
        elif auth_type == 'api_key':
            key = auth_config.get('key', '')
            header_name = auth_config.get('header_name', 'X-API-Key')
            if key:
                headers[header_name] = key
        
        # Ensure Content-Type for JSON requests
        if not headers.get('Content-Type'):
            headers['Content-Type'] = 'application/json'
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any,
        timeout: int,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Make the actual HTTP request"""
        
        async with aiohttp.ClientSession() as session:
            # Prepare request
            request_kwargs = {
                'method': method,
                'url': url,
                'headers': headers,
                'timeout': aiohttp.ClientTimeout(total=timeout)
            }
            
            # Add body for appropriate methods
            if method in ['POST', 'PUT', 'PATCH'] and body is not None:
                if isinstance(body, dict):
                    request_kwargs['json'] = body
                else:
                    request_kwargs['data'] = body
            
            self.logger.info(
                "Making API request",
                node_id=context.node_id,
                method=method,
                url=url,
                headers_count=len(headers)
            )
            
            # Make request
            async with session.request(**request_kwargs) as response:
                status = response.status
                response_headers = dict(response.headers)
                
                # Try to get response as JSON, fallback to text
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                self.logger.info(
                    "API request completed",
                    node_id=context.node_id,
                    status=status,
                    content_type=response_headers.get('content-type', 'unknown')
                )
                
                # Return comprehensive response data
                result = {
                    'response': response_data,
                    'status': status,
                    'headers': response_headers,
                    'success': 200 <= status < 300,
                    'error': None if 200 <= status < 300 else f"HTTP {status}: {response_data}"
                }
                
                return self.format_output(**result)