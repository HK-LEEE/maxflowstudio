"""
파일명: base_llm.py (80줄)
목적: LLM 컴포넌트들의 공통 베이스 클래스
동작 과정:
1. 모든 LLM 컴포넌트의 공통 인터페이스 정의
2. 메시지 포맷팅 및 검증 로직
3. 스트리밍 응답 처리 기본 구조
4. 토큰 사용량 추적 인터페이스
데이터베이스 연동: 없음 (순수 추상 클래스)
의존성: component_base.py
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from ...core.component_base import BaseComponent
import structlog

logger = structlog.get_logger()


class BaseLLMComponent(BaseComponent):
    """Base class for all LLM components with common functionality."""
    
    def __init__(self, component_id: str):
        super().__init__(component_id)
        self.api_key: Optional[str] = None
        self.model: Optional[str] = None
        self.temperature: float = 0.7
        self.max_tokens: int = 1000
        self.stream: bool = False
        
    def prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages in the format expected by the LLM API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        if conversation_history:
            messages.extend(conversation_history)
            
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    @abstractmethod
    async def call_api(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Make the actual API call to the LLM service."""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate that the API key is present and properly formatted."""
        pass
    
    def track_usage(
        self, 
        prompt_tokens: int, 
        completion_tokens: int,
        model: str
    ) -> Dict[str, Any]:
        """Track token usage and costs."""
        total_tokens = prompt_tokens + completion_tokens
        
        usage_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model": model,
            "timestamp": self.get_current_timestamp()
        }
        
        logger.info(
            "llm_usage_tracked",
            component_id=self.component_id,
            **usage_data
        )
        
        return usage_data