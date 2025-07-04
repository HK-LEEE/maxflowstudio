"""
OpenAI API Client
Flow: API configuration → Request formatting → HTTP client → Response handling
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class OpenAIAPIError(Exception):
    """OpenAI API specific error."""
    def __init__(self, message: str, status_code: int = None, error_type: str = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message)


class OpenAIClient:
    """
    OpenAI API client for chat completions.
    
    Client Process:
    1. initialize() → Set up HTTP client with API key and headers
    2. prepare_request() → Format chat completion request payload
    3. make_request() → Execute HTTP request with retry logic
    4. handle_streaming() → Process streaming response chunks
    5. parse_response() → Extract content from API response
    
    Responsibilities:
    - HTTP client management and connection pooling
    - API request/response formatting
    - Error handling and retry mechanisms
    - Streaming response processing
    - Token usage tracking
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        """Initialize OpenAI client."""
        self.api_key = api_key
        self.base_url = base_url
        self.logger = logger.bind(component="openai_client")
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "MAXFlowstudio/1.0"
            }
        )
    
    async def validate_api_key(self) -> bool:
        """Validate API key by making a test request."""
        try:
            response = await self.client.get(f"{self.base_url}/models", timeout=10.0)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning("API key validation failed", error=str(e))
            return False
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create chat completion request.
        
        Args:
            messages: List of message objects with role and content
            model: OpenAI model name
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream response
            **kwargs: Additional OpenAI parameters
            
        Returns:
            Dict containing response data or streaming generator
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            if stream:
                return await self._stream_completion(payload)
            else:
                return await self._single_completion(payload)
                
        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except httpx.TimeoutException:
            raise OpenAIAPIError("Request timeout", status_code=408)
        except Exception as e:
            raise OpenAIAPIError(f"Unexpected error: {str(e)}")
    
    async def _single_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle single (non-streaming) completion request."""
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract and format response
        return {
            "content": result["choices"][0]["message"]["content"],
            "model": result["model"],
            "usage": result.get("usage", {}),
            "finish_reason": result["choices"][0]["finish_reason"],
            "response_time": response.elapsed.total_seconds(),
            "created": result["created"]
        }
    
    async def _stream_completion(self, payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming completion request."""
        async with self.client.stream(
            "POST", 
            f"{self.base_url}/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        
                        if "content" in delta:
                            yield {
                                "content": delta["content"],
                                "chunk_id": chunk["id"],
                                "model": chunk["model"],
                                "created": chunk["created"],
                                "finish_reason": chunk["choices"][0].get("finish_reason")
                            }
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning("Failed to parse streaming chunk", error=str(e))
                        continue
    
    async def _handle_api_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle API error responses."""
        try:
            error_data = error.response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown API error")
            error_type = error_data.get("error", {}).get("type", "api_error")
        except (json.JSONDecodeError, AttributeError):
            error_message = f"HTTP {error.response.status_code}: {error.response.text}"
            error_type = "http_error"
        
        raise OpenAIAPIError(
            message=error_message,
            status_code=error.response.status_code,
            error_type=error_type
        )
    
    async def estimate_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Estimate token count for text.
        
        Note: This is a rough estimation. For accurate counts,
        use the tiktoken library in production.
        """
        # Rough estimation: ~4 characters per token for most models
        return len(text) // 4
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            if hasattr(self, 'client'):
                asyncio.create_task(self.client.aclose())
        except Exception:
            pass