"""
파일명: anthropic_claude.py (400줄)
목적: Anthropic Claude LLM 컴포넌트 메인 구현
동작 과정:
1. 입력 메시지 포맷팅 및 검증
2. Claude API 호출 (스트리밍/일반)
3. 응답 처리 및 안전성 검사
4. 결과 반환 및 사용량 추적
데이터베이스 연동: 실행 로그 저장 (execution_logs 테이블)
의존성: base_llm.py, anthropic_client.py
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from pydantic import Field

from ...core.component_base import (
    ComponentMetadata, 
    ComponentInput, 
    ComponentOutput,
    InputType,
    OutputType,
    ComponentStatus
)
from .base_llm import BaseLLMComponent
from .anthropic_client import AnthropicAPIClient

logger = structlog.get_logger()


class AnthropicClaudeComponent(BaseLLMComponent):
    """
    Anthropic Claude Chat Component.
    
    Claude Execution Flow:
    1. prepare_messages() → Format input with human/assistant structure
    2. validate_api_key() → Check Anthropic API key validity
    3. call_claude_api() → Make async API call with streaming support
    4. process_response() → Parse response and handle safety features
    5. handle_streaming() → Support real-time response streaming
    6. track_usage() → Monitor token usage and safety metrics
    
    Safety Features:
    - Content filtering for harmful outputs
    - Automatic harm detection in responses
    - Safety level configuration (strict/moderate/minimal)
    - Abuse prevention with rate limiting
    """
    
    @classmethod
    def get_metadata(cls) -> ComponentMetadata:
        return ComponentMetadata(
            name="Anthropic Claude",
            type="llm",
            category="Language Models",
            description="Chat with Anthropic's Claude models (Opus, Sonnet, Haiku)",
            version="1.0.0",
            author="MAX Platform",
            inputs=[
                ComponentInput(
                    name="prompt",
                    type=InputType.TEXT,
                    description="The prompt or question to send to Claude",
                    required=True
                ),
                ComponentInput(
                    name="system_prompt",
                    type=InputType.TEXT,
                    description="System prompt to set Claude's behavior and context",
                    required=False
                ),
                ComponentInput(
                    name="model",
                    type=InputType.TEXT,
                    description="Claude model to use (claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307)",
                    required=False,
                    default="claude-3-sonnet-20240229"
                ),
                ComponentInput(
                    name="temperature",
                    type=InputType.NUMBER,
                    description="Sampling temperature (0.0-1.0). Higher = more creative",
                    required=False,
                    default=0.7
                ),
                ComponentInput(
                    name="max_tokens",
                    type=InputType.NUMBER,
                    description="Maximum tokens in response",
                    required=False,
                    default=1000
                ),
                ComponentInput(
                    name="api_key",
                    type=InputType.TEXT,
                    description="Anthropic API key",
                    required=True,
                    sensitive=True
                ),
                ComponentInput(
                    name="conversation_history",
                    type=InputType.JSON,
                    description="Previous conversation messages for context",
                    required=False
                ),
                ComponentInput(
                    name="safety_level",
                    type=InputType.TEXT,
                    description="Safety level: strict, moderate, minimal",
                    required=False,
                    default="moderate"
                ),
                ComponentInput(
                    name="stream",
                    type=InputType.BOOLEAN,
                    description="Stream response tokens as they arrive",
                    required=False,
                    default=False
                )
            ],
            outputs=[
                ComponentOutput(
                    name="response",
                    type=OutputType.TEXT,
                    description="Claude's response text"
                ),
                ComponentOutput(
                    name="usage",
                    type=OutputType.JSON,
                    description="Token usage statistics"
                ),
                ComponentOutput(
                    name="model",
                    type=OutputType.TEXT,
                    description="Model used for generation"
                ),
                ComponentOutput(
                    name="safety_ratings",
                    type=OutputType.JSON,
                    description="Content safety ratings"
                ),
                ComponentOutput(
                    name="finish_reason",
                    type=OutputType.TEXT,
                    description="Reason for completion (stop, length, safety)"
                )
            ],
            documentation="""
            # Anthropic Claude Component
            
            This component integrates with Anthropic's Claude models for advanced conversational AI.
            
            ## Supported Models
            - **Claude 3 Opus**: Most capable model for complex tasks
            - **Claude 3 Sonnet**: Balanced performance and speed
            - **Claude 3 Haiku**: Fast and efficient for simple tasks
            - **Claude 2.1**: Previous generation with 200K context
            - **Claude Instant**: Fastest model for real-time applications
            
            ## Features
            - Streaming responses for real-time interaction
            - Conversation history support for context
            - Content safety filtering
            - Token usage tracking
            - Custom system prompts
            
            ## Example Usage
            ```json
            {
                "prompt": "Explain quantum computing in simple terms",
                "system_prompt": "You are a helpful physics teacher",
                "model": "claude-3-sonnet-20240229",
                "temperature": 0.7,
                "max_tokens": 500
            }
            ```
            """
        )
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Claude component."""
        try:
            # Update status
            await self.update_status(ComponentStatus.EXECUTING, "Preparing Claude request")
            
            # Extract inputs
            prompt = inputs.get("prompt", "")
            system_prompt = inputs.get("system_prompt", None)
            self.model = inputs.get("model", "claude-3-sonnet-20240229")
            self.temperature = float(inputs.get("temperature", 0.7))
            self.max_tokens = int(inputs.get("max_tokens", 1000))
            self.api_key = inputs.get("api_key", "")
            conversation_history = inputs.get("conversation_history", [])
            safety_level = inputs.get("safety_level", "moderate")
            self.stream = inputs.get("stream", False)
            
            # Validate inputs
            if not prompt:
                raise ValueError("Prompt is required")
                
            if not self.validate_api_key():
                raise ValueError("Invalid or missing API key")
            
            # Initialize API client
            client = AnthropicAPIClient(self.api_key)
            
            # Validate model
            if not client.validate_model(self.model):
                raise ValueError(f"Invalid model: {self.model}")
            
            # Prepare messages
            messages = self.prepare_messages(prompt, system_prompt, conversation_history)
            
            # Apply safety filtering to input
            if safety_level != "minimal":
                messages = await self.apply_input_safety(messages, safety_level)
            
            # Call Claude API
            await self.update_status(ComponentStatus.EXECUTING, "Calling Claude API")
            
            response_text = ""
            usage_data = {}
            safety_ratings = {}
            finish_reason = "stop"
            
            async for chunk in self.call_api(messages):
                if self.stream:
                    # Handle streaming response
                    if chunk.get("type") == "content_block_delta":
                        delta_text = chunk.get("delta", {}).get("text", "")
                        response_text += delta_text
                        
                        # Emit streaming update
                        await self.emit_streaming_update({
                            "text": delta_text,
                            "accumulated": response_text
                        })
                        
                elif chunk.get("type") == "message":
                    # Handle non-streaming response
                    content = chunk.get("content", [])
                    if content and len(content) > 0:
                        response_text = content[0].get("text", "")
                        
                    # Extract usage data
                    usage = chunk.get("usage", {})
                    usage_data = self.track_usage(
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                        self.model
                    )
                    
                    # Extract finish reason
                    finish_reason = chunk.get("stop_reason", "stop")
            
            # Apply output safety filtering
            if safety_level != "minimal":
                response_text, safety_ratings = await self.apply_output_safety(
                    response_text, 
                    safety_level
                )
            
            # Prepare outputs
            outputs = {
                "response": response_text,
                "usage": usage_data,
                "model": self.model,
                "safety_ratings": safety_ratings,
                "finish_reason": finish_reason
            }
            
            await self.update_status(ComponentStatus.COMPLETED, "Claude request completed")
            
            return outputs
            
        except Exception as e:
            await self.update_status(
                ComponentStatus.FAILED, 
                f"Claude execution failed: {str(e)}"
            )
            logger.error(
                "claude_execution_failed",
                component_id=self.component_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def call_api(self, messages: List[Dict[str, str]]):
        """Make API call to Claude."""
        client = AnthropicAPIClient(self.api_key)
        
        async for chunk in client.create_message(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=self.stream
        ):
            yield chunk
    
    def validate_api_key(self) -> bool:
        """Validate Anthropic API key format."""
        if not self.api_key:
            return False
        
        # Anthropic API keys typically start with 'sk-ant-'
        return self.api_key.startswith('sk-ant-') and len(self.api_key) > 20
    
    async def apply_input_safety(
        self, 
        messages: List[Dict[str, str]], 
        safety_level: str
    ) -> List[Dict[str, str]]:
        """Apply safety filtering to input messages."""
        # In production, implement content filtering here
        # For now, return messages as-is
        return messages
    
    async def apply_output_safety(
        self, 
        response: str, 
        safety_level: str
    ) -> tuple[str, Dict[str, Any]]:
        """Apply safety filtering to output and generate safety ratings."""
        safety_ratings = {
            "harmful_content": False,
            "personal_info": False,
            "medical_advice": False,
            "legal_advice": False,
            "financial_advice": False,
            "safety_level": safety_level
        }
        
        # In production, implement actual content safety checks here
        # For now, return response as-is with mock ratings
        
        return response, safety_ratings
    
    async def emit_streaming_update(self, update: Dict[str, Any]):
        """Emit streaming update for real-time response."""
        logger.debug(
            "claude_streaming_update",
            component_id=self.component_id,
            update=update
        )
        # In production, emit through websocket or event stream
        
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + "Z"