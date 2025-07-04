"""
파일명: anthropic_client.py (150줄)
목적: Anthropic API 클라이언트 및 통신 로직
동작 과정:
1. HTTP 클라이언트 초기화 및 설정
2. API 엔드포인트 호출 로직
3. 스트리밍 응답 처리
4. 에러 핸들링 및 재시도 로직
데이터베이스 연동: 없음 (API 통신만 담당)
의존성: httpx, structlog
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
import json
import structlog

logger = structlog.get_logger()


class AnthropicAPIClient:
    """Handles API communication with Anthropic Claude."""
    
    API_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_TIMEOUT = 120.0
    MAX_RETRIES = 3
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
    async def create_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a message with Claude API."""
        
        endpoint = f"{self.API_BASE_URL}/messages"
        
        # Prepare request body
        request_body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        # Make API call with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                    if stream:
                        async with client.stream(
                            "POST", 
                            endpoint, 
                            json=request_body,
                            headers=self.headers
                        ) as response:
                            response.raise_for_status()
                            
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        yield json.loads(data)
                                    except json.JSONDecodeError:
                                        logger.warning(
                                            "Failed to parse streaming data",
                                            data=data
                                        )
                    else:
                        response = await client.post(
                            endpoint,
                            json=request_body,
                            headers=self.headers
                        )
                        response.raise_for_status()
                        yield response.json()
                        
                break  # Success, exit retry loop
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = min(2 ** attempt, 60)
                    logger.warning(
                        f"Rate limited, waiting {wait_time}s",
                        attempt=attempt
                    )
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Server error, retrying in {wait_time}s",
                            status_code=e.response.status_code,
                            attempt=attempt
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise
                else:
                    # Client error, don't retry
                    error_detail = e.response.json() if e.response.content else {}
                    raise ValueError(f"API error: {e.response.status_code} - {error_detail}")
                    
            except httpx.TimeoutException:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"Request timeout, retrying",
                        attempt=attempt
                    )
                    continue
                else:
                    raise ValueError("API request timed out after retries")
                    
            except Exception as e:
                logger.error(
                    "Unexpected error calling Anthropic API",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
    
    def validate_model(self, model: str) -> bool:
        """Validate that the model name is supported."""
        valid_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
        return model in valid_models