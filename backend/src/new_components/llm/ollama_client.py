"""
파일명: ollama_client.py (120줄)
목적: Ollama 로컬 서버 API 클라이언트
동작 과정:
1. Ollama 서버 연결 및 상태 확인
2. 모델 목록 조회 및 다운로드 관리
3. 로컬 LLM 호출 및 스트리밍 처리
4. 네트워크 연결 관리 및 재시도 로직
데이터베이스 연동: 없음 (로컬 API 통신만)
의존성: httpx, structlog
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
import json
import structlog

logger = structlog.get_logger()


class OllamaAPIClient:
    """Handles API communication with local Ollama server."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 120.0
        
    async def check_server_status(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException):
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull/download a model from Ollama registry."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name}
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse pull response: {line}")
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            raise
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = True,
        raw: bool = False,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate text using Ollama model."""
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        if system:
            request_data["system"] = system
        if template:
            request_data["template"] = template
        if context:
            request_data["context"] = context
        if raw:
            request_data["raw"] = raw
        if format:
            request_data["format"] = format
        if options:
            request_data["options"] = options
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                yield chunk
                                
                                # Break on completion
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse generate response: {line}")
        except Exception as e:
            logger.error(f"Failed to generate with model {model}: {e}")
            raise
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Chat using Ollama model with message history."""
        
        request_data = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if format:
            request_data["format"] = format
        if options:
            request_data["options"] = options
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                yield chunk
                                
                                # Break on completion
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse chat response: {line}")
        except Exception as e:
            logger.error(f"Failed to chat with model {model}: {e}")
            raise