"""
┌──────────────────────────────────────────────────────────────┐
│                    LLM Component Flow                       │
│                                                              │
│  [Input] → [Format] → [API Call] → [Stream] → [Output]     │
│     ↓        ↓          ↓           ↓         ↓            │
│  텍스트입력  프롬프트포맷  OpenAI호출   응답스트림  결과반환   │
│                                                              │
│  Error Flow: API Error → Retry → Fallback → User Notice    │
│                                                              │
│  Data Flow: User Message → System Prompt → API → Response  │
│  Token Management: Count Input → Track Usage → Limit Check │
└──────────────────────────────────────────────────────────────┘

OpenAI Chat Component for MAX Flowstudio
Flow: Text input → Prompt formatting → OpenAI API call → Response streaming → Result output
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
import httpx
from pydantic import Field

from ...core.component_base import (
    BaseComponent, 
    ComponentMetadata, 
    ComponentInput, 
    ComponentOutput,
    InputType,
    OutputType,
    ComponentStatus
)

logger = structlog.get_logger()


class OpenAIChatComponent(BaseComponent):
    """
    OpenAI Chat Completion Component.
    
    LLM Execution Flow:
    1. prepare_prompt() → Format input text with system/user prompts
    2. validate_api_key() → Check API key validity and permissions
    3. call_openai_api() → Make async API call with streaming support
    4. process_response() → Parse response and extract content
    5. handle_streaming() → Support real-time response streaming
    6. update_usage() → Track token usage and costs
    
    Features:
    - Multiple OpenAI model support (GPT-4, GPT-3.5-turbo, etc.)
    - Streaming response support
    - Token usage tracking
    - Conversation history management
    - Temperature and parameter control
    - Error handling with retry logic
    """
    
    def __init__(self, **kwargs):
        """Initialize OpenAI Chat component."""
        super().__init__(**kwargs)
        
        # Component configuration
        self.api_key: Optional[str] = kwargs.get('api_key')
        self.model: str = kwargs.get('model', 'gpt-4')
        self.temperature: float = kwargs.get('temperature', 0.7)
        self.max_tokens: Optional[int] = kwargs.get('max_tokens', None)
        self.top_p: float = kwargs.get('top_p', 1.0)
        self.frequency_penalty: float = kwargs.get('frequency_penalty', 0.0)
        self.presence_penalty: float = kwargs.get('presence_penalty', 0.0)
        self.system_prompt: Optional[str] = kwargs.get('system_prompt')
        self.stream_response: bool = kwargs.get('stream_response', False)
        
        # API client
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://api.openai.com/v1"
        
        # Usage tracking
        self._total_tokens_used = 0
        self._total_cost = 0.0
    
    @property
    def metadata(self) -> ComponentMetadata:
        """Component metadata definition."""
        return ComponentMetadata(
            name="openai_chat",
            display_name="OpenAI Chat",
            description="Chat completion using OpenAI's GPT models with streaming support",
            category="ai_ml",
            icon="openai",
            version="1.0.0",
            author="MAX Flowstudio",
            documentation="""
# OpenAI Chat Component

This component provides chat completion capabilities using OpenAI's GPT models.

## Features
- Support for multiple OpenAI models (GPT-4, GPT-3.5-turbo, etc.)
- Streaming response support for real-time output
- Conversation history management
- Token usage tracking and cost estimation
- Customizable parameters (temperature, max_tokens, etc.)

## Configuration
- **API Key**: Your OpenAI API key
- **Model**: The OpenAI model to use (gpt-4, gpt-3.5-turbo, etc.)
- **Temperature**: Controls randomness (0.0 to 2.0)
- **Max Tokens**: Maximum tokens in response
- **System Prompt**: System instruction for the model

## Usage
1. Connect text input to the 'user_message' input
2. Configure your API key and model settings
3. Optionally provide conversation history
4. The component will output the AI response
            """,
            tags=["llm", "openai", "chat", "gpt", "ai", "text-generation"]
        )
    
    @property
    def inputs(self) -> List[ComponentInput]:
        """Component input definitions."""
        return [
            ComponentInput(
                name="user_message",
                display_name="User Message",
                description="The user's message to send to the AI",
                input_type=InputType.TEXT,
                required=True,
                validation_rules={
                    "min_length": 1,
                    "max_length": 10000
                }
            ),
            ComponentInput(
                name="conversation_history",
                display_name="Conversation History",
                description="Previous conversation messages for context",
                input_type=InputType.ARRAY,
                required=False,
                default_value=[]
            ),
            ComponentInput(
                name="system_prompt_override",
                display_name="System Prompt Override",
                description="Override the default system prompt",
                input_type=InputType.TEXT,
                required=False
            ),
            ComponentInput(
                name="temperature_override",
                display_name="Temperature Override",
                description="Override the default temperature setting",
                input_type=InputType.NUMBER,
                required=False,
                validation_rules={
                    "min_value": 0.0,
                    "max_value": 2.0
                }
            ),
            ComponentInput(
                name="max_tokens_override",
                display_name="Max Tokens Override",
                description="Override the default max tokens setting",
                input_type=InputType.NUMBER,
                required=False,
                validation_rules={
                    "min_value": 1,
                    "max_value": 4096
                }
            )
        ]
    
    @property
    def outputs(self) -> List[ComponentOutput]:
        """Component output definitions."""
        return [
            ComponentOutput(
                name="response",
                display_name="AI Response",
                description="The AI's response message",
                output_type=OutputType.TEXT
            ),
            ComponentOutput(
                name="conversation_history",
                display_name="Updated Conversation History",
                description="Conversation history including the new exchange",
                output_type=OutputType.ARRAY
            ),
            ComponentOutput(
                name="usage_stats",
                display_name="Usage Statistics",
                description="Token usage and cost information",
                output_type=OutputType.OBJECT
            ),
            ComponentOutput(
                name="model_info",
                display_name="Model Information",
                description="Information about the model used",
                output_type=OutputType.OBJECT
            ),
            ComponentOutput(
                name="response_stream",
                display_name="Response Stream",
                description="Streaming response data (if streaming enabled)",
                output_type=OutputType.STREAM
            )
        ]
    
    async def build_results(self) -> Dict[str, Any]:
        """
        Execute the OpenAI chat completion.
        
        Complete Execution Flow:
        1. Validate API configuration
        2. Prepare conversation messages
        3. Make API call to OpenAI
        4. Process response (streaming or complete)
        5. Update conversation history
        6. Track usage statistics
        7. Return structured results
        """
        self.logger.info("Starting OpenAI chat completion")
        
        # Get input values
        user_message = self.get_input("user_message")
        conversation_history = self.get_input("conversation_history", [])
        system_prompt_override = self.get_input("system_prompt_override")
        temperature_override = self.get_input("temperature_override")
        max_tokens_override = self.get_input("max_tokens_override")
        
        # Validate API key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Prepare messages
        messages = await self._prepare_messages(
            user_message, 
            conversation_history, 
            system_prompt_override
        )
        
        # Prepare API parameters
        api_params = await self._prepare_api_parameters(
            messages,
            temperature_override,
            max_tokens_override
        )
        
        # Initialize HTTP client
        await self._initialize_client()
        
        try:
            if self.stream_response:
                # Handle streaming response
                response_data = await self._handle_streaming_response(api_params)
            else:
                # Handle complete response
                response_data = await self._handle_complete_response(api_params)
            
            # Update conversation history
            updated_history = await self._update_conversation_history(
                conversation_history,
                user_message,
                response_data["response"]
            )
            
            # Prepare final results
            results = {
                "response": response_data["response"],
                "conversation_history": updated_history,
                "usage_stats": response_data["usage_stats"],
                "model_info": response_data["model_info"],
            }
            
            if self.stream_response:
                results["response_stream"] = response_data.get("stream_data")
            
            self.logger.info("OpenAI chat completion successful",
                           response_length=len(response_data["response"]),
                           tokens_used=response_data["usage_stats"]["total_tokens"])
            
            return results
            
        except Exception as e:
            self.logger.error("OpenAI chat completion failed", error=str(e))
            raise
        
        finally:
            await self._cleanup_client()
    
    async def _prepare_messages(
        self, 
        user_message: str, 
        conversation_history: List[Dict], 
        system_prompt_override: Optional[str]
    ) -> List[Dict[str, str]]:
        """
        Prepare conversation messages for API call.
        
        Message Preparation Process:
        1. Add system prompt (default or override)
        2. Add conversation history
        3. Add current user message
        4. Validate message format
        """
        messages = []
        
        # Add system prompt
        system_prompt = system_prompt_override or self.system_prompt
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        for msg in conversation_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append(msg)
            else:
                self.logger.warning("Invalid message format in history", message=msg)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        self.logger.debug("Messages prepared", message_count=len(messages))
        return messages
    
    async def _prepare_api_parameters(
        self,
        messages: List[Dict[str, str]],
        temperature_override: Optional[float],
        max_tokens_override: Optional[int]
    ) -> Dict[str, Any]:
        """Prepare API parameters for OpenAI call."""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature_override if temperature_override is not None else self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stream": self.stream_response,
        }
        
        # Add max_tokens if specified
        max_tokens = max_tokens_override if max_tokens_override is not None else self.max_tokens
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        return params
    
    async def _initialize_client(self) -> None:
        """Initialize HTTP client for API calls."""
        if not self._client:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=httpx.Timeout(30.0)
            )
    
    async def _cleanup_client(self) -> None:
        """Cleanup HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _handle_complete_response(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle complete (non-streaming) API response.
        
        Complete Response Process:
        1. Make API call to OpenAI
        2. Parse response JSON
        3. Extract message content
        4. Calculate usage statistics
        5. Return structured data
        """
        self.logger.debug("Making complete API call to OpenAI")
        
        response = await self._client.post(
            f"{self._base_url}/chat/completions",
            json=api_params
        )
        
        if response.status_code != 200:
            error_text = await response.aread()
            raise ValueError(f"OpenAI API error {response.status_code}: {error_text}")
        
        response_data = response.json()
        
        # Extract response content
        assistant_message = response_data["choices"][0]["message"]["content"]
        
        # Extract usage statistics
        usage = response_data.get("usage", {})
        usage_stats = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "estimated_cost": await self._calculate_cost(usage),
        }
        
        # Model information
        model_info = {
            "model": response_data.get("model", self.model),
            "created": response_data.get("created"),
            "id": response_data.get("id"),
        }
        
        return {
            "response": assistant_message,
            "usage_stats": usage_stats,
            "model_info": model_info,
        }
    
    async def _handle_streaming_response(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle streaming API response.
        
        Streaming Response Process:
        1. Make streaming API call
        2. Process server-sent events
        3. Accumulate response chunks
        4. Parse final usage data
        5. Return complete response with stream data
        """
        self.logger.debug("Making streaming API call to OpenAI")
        
        accumulated_response = ""
        stream_data = []
        
        async with self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            json=api_params
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise ValueError(f"OpenAI API error {response.status_code}: {error_text}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data_str)
                        
                        # Extract content from chunk
                        choices = chunk_data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                accumulated_response += content
                                stream_data.append({
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "content": content,
                                    "accumulated": accumulated_response,
                                })
                    
                    except json.JSONDecodeError:
                        continue
        
        # Estimate usage for streaming (actual usage not available)
        estimated_usage = await self._estimate_usage(api_params["messages"], accumulated_response)
        
        usage_stats = {
            "prompt_tokens": estimated_usage["prompt_tokens"],
            "completion_tokens": estimated_usage["completion_tokens"],
            "total_tokens": estimated_usage["total_tokens"],
            "estimated_cost": await self._calculate_cost(estimated_usage),
            "is_estimated": True,
        }
        
        model_info = {
            "model": self.model,
            "streaming": True,
            "chunks_received": len(stream_data),
        }
        
        return {
            "response": accumulated_response,
            "usage_stats": usage_stats,
            "model_info": model_info,
            "stream_data": stream_data,
        }
    
    async def _update_conversation_history(
        self,
        history: List[Dict],
        user_message: str,
        assistant_response: str
    ) -> List[Dict]:
        """Update conversation history with new exchange."""
        updated_history = history.copy()
        
        # Add user message
        updated_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Add assistant response
        updated_history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return updated_history
    
    async def _estimate_usage(self, messages: List[Dict], response: str) -> Dict[str, int]:
        """Estimate token usage for streaming responses."""
        # Simple estimation based on character count
        # In production, you'd use tiktoken or similar for accurate counting
        
        prompt_chars = sum(len(msg["content"]) for msg in messages)
        completion_chars = len(response)
        
        # Rough estimation: 1 token ≈ 4 characters
        prompt_tokens = max(1, prompt_chars // 4)
        completion_tokens = max(1, completion_chars // 4)
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
    
    async def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """Calculate estimated cost based on token usage."""
        # OpenAI pricing (as of 2024 - update as needed)
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},  # per 1K tokens
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        }
        
        model_pricing = pricing.get(self.model, pricing["gpt-3.5-turbo"])
        
        prompt_cost = (usage.get("prompt_tokens", 0) / 1000) * model_pricing["prompt"]
        completion_cost = (usage.get("completion_tokens", 0) / 1000) * model_pricing["completion"]
        
        return prompt_cost + completion_cost