"""
OpenAI Chat Component - Refactored (558 → 350 lines)
Flow: User input → Prompt processing → API call → Response formatting
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
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
from .openai_client import OpenAIClient, OpenAIAPIError
from .openai_prompt import OpenAIPromptProcessor

logger = structlog.get_logger()


class OpenAIChatComponent(BaseComponent):
    """
    OpenAI Chat Completion Component - Modular Implementation.
    
    Component Process:
    1. initialize() → Set up API client and prompt processor
    2. validate_config() → Check API key and model configuration
    3. process_input() → Use prompt processor for message formatting
    4. call_api() → Execute API request via client
    5. format_output() → Structure response for next component
    
    Responsibilities:
    - Component interface implementation
    - Configuration management
    - Input/output handling
    - Error reporting and status updates
    """
    
    def __init__(self, **kwargs):
        """Initialize OpenAI Chat component."""
        super().__init__(**kwargs)
        
        # Component configuration
        self.api_key: Optional[str] = kwargs.get('api_key')
        self.model: str = kwargs.get('model', 'gpt-4')
        self.temperature: float = kwargs.get('temperature', 0.7)
        self.max_tokens: Optional[int] = kwargs.get('max_tokens', None)
        self.system_prompt: Optional[str] = kwargs.get('system_prompt')
        self.stream_response: bool = kwargs.get('stream_response', False)
        self.include_history: bool = kwargs.get('include_history', True)
        
        # Initialize subsystems
        self._client: Optional[OpenAIClient] = None
        self._prompt_processor = OpenAIPromptProcessor()
        
        # Usage tracking
        self._total_tokens_used = 0
        self._total_cost = 0.0
        
        self.logger = logger.bind(component="openai_chat", component_id=self.id)
    
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

Advanced chat completion using OpenAI's GPT models with comprehensive features:

## Features
- Multiple model support (GPT-4, GPT-3.5-turbo)
- Streaming responses for real-time output
- Conversation history management
- Token usage tracking and cost estimation
- Custom system prompts and role configuration

## Configuration
- **API Key**: Your OpenAI API key (required)
- **Model**: Choose from available GPT models
- **Temperature**: Control response creativity (0.0-2.0)
- **Max Tokens**: Limit response length
- **System Prompt**: Custom instructions for the AI
- **Stream Response**: Enable real-time streaming
- **Include History**: Maintain conversation context

## Usage
1. Connect text input to the 'user_input' port
2. Configure your API key and model preferences
3. Optionally set custom system prompt
4. The component outputs formatted AI responses
            """.strip()
        )
    
    @property
    def inputs(self) -> List[ComponentInput]:
        """Define component inputs."""
        return [
            ComponentInput(
                name="user_input",
                display_name="User Input",
                input_type=InputType.TEXT,
                description="Text input for the AI to respond to",
                required=True
            ),
            ComponentInput(
                name="system_prompt",
                display_name="System Prompt",
                input_type=InputType.TEXT,
                description="Optional system prompt to override default",
                required=False
            ),
            ComponentInput(
                name="context",
                display_name="Context",
                input_type=InputType.TEXT,
                description="Additional context for the conversation",
                required=False
            )
        ]
    
    @property
    def outputs(self) -> List[ComponentOutput]:
        """Define component outputs."""
        return [
            ComponentOutput(
                name="response",
                display_name="AI Response",
                output_type=OutputType.TEXT,
                description="Generated response from OpenAI"
            ),
            ComponentOutput(
                name="metadata",
                display_name="Response Metadata",
                output_type=OutputType.JSON,
                description="Token usage, model info, and other metadata"
            ),
            ComponentOutput(
                name="conversation_history",
                display_name="Conversation History",
                output_type=OutputType.JSON,
                description="Current conversation context"
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize component and validate configuration."""
        await super().initialize()
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize API client
        self._client = OpenAIClient(self.api_key)
        
        # Validate API key
        is_valid = await self._client.validate_api_key()
        if not is_valid:
            raise ValueError("Invalid OpenAI API key")
        
        self.logger.info("OpenAI Chat component initialized", model=self.model)
    
    async def build_results(self) -> None:
        """Execute the OpenAI chat completion."""
        try:
            self.status = ComponentStatus.RUNNING
            
            # Get inputs
            user_input = self.get_input_value("user_input")
            system_prompt_override = self.get_input_value("system_prompt")
            context = self.get_input_value("context", "")
            
            if not user_input:
                raise ValueError("User input is required")
            
            # Prepare messages using prompt processor
            messages = self._prompt_processor.prepare_messages(
                user_input=user_input,
                system_prompt=system_prompt_override or self.system_prompt,
                context=context,
                include_history=self.include_history
            )
            
            # Make API call
            self.logger.info("Making OpenAI API call", model=self.model, message_count=len(messages))
            
            if self.stream_response:
                response_data = await self._handle_streaming_response(messages)
            else:
                response_data = await self._handle_single_response(messages)
            
            # Update conversation history
            self._prompt_processor.add_to_history(user_input, response_data["content"])
            
            # Set outputs
            self.set_output_value("response", response_data["content"])
            self.set_output_value("metadata", {
                "model": response_data.get("model"),
                "usage": response_data.get("usage", {}),
                "finish_reason": response_data.get("finish_reason"),
                "response_time": response_data.get("response_time"),
                "timestamp": datetime.utcnow().isoformat()
            })
            self.set_output_value("conversation_history", self._prompt_processor.conversation_history)
            
            # Update usage tracking
            usage = response_data.get("usage", {})
            if usage:
                self._total_tokens_used += usage.get("total_tokens", 0)
                self._total_cost += self._estimate_cost(usage)
            
            self.status = ComponentStatus.SUCCESS
            self.logger.info("OpenAI chat completion successful")
            
        except OpenAIAPIError as e:
            self.status = ComponentStatus.ERROR
            error_msg = f"OpenAI API error: {e.message}"
            self.logger.error("OpenAI API error", error=error_msg, status_code=e.status_code)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            self.status = ComponentStatus.ERROR
            error_msg = f"OpenAI chat error: {str(e)}"
            self.logger.error("OpenAI chat execution failed", error=error_msg)
            raise RuntimeError(error_msg)
    
    async def _handle_single_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle non-streaming API response."""
        return await self._client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=False
        )
    
    async def _handle_streaming_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle streaming API response."""
        full_response = ""
        metadata = {}
        
        async for chunk in await self._client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True
        ):
            if chunk.get("content"):
                full_response += chunk["content"]
                # Could emit partial results here for real-time updates
            
            # Capture metadata from the final chunk
            if chunk.get("finish_reason"):
                metadata.update({
                    "model": chunk.get("model"),
                    "finish_reason": chunk.get("finish_reason"),
                    "created": chunk.get("created")
                })
        
        return {
            "content": full_response,
            **metadata
        }
    
    def _estimate_cost(self, usage: Dict[str, Any]) -> float:
        """Estimate cost based on token usage."""
        # Simplified cost estimation (update with actual OpenAI pricing)
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        # Example pricing for GPT-4 (update as needed)
        if "gpt-4" in self.model.lower():
            input_cost = input_tokens * 0.00003  # $0.03 per 1K tokens
            output_cost = output_tokens * 0.00006  # $0.06 per 1K tokens
        else:  # GPT-3.5-turbo
            input_cost = input_tokens * 0.0000015  # $0.0015 per 1K tokens
            output_cost = output_tokens * 0.000002  # $0.002 per 1K tokens
        
        return input_cost + output_cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get component usage statistics."""
        return {
            "total_tokens_used": self._total_tokens_used,
            "estimated_total_cost": self._total_cost,
            "model": self.model,
            "conversation_length": len(self._prompt_processor.conversation_history)
        }
    
    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self._prompt_processor.clear_history()
        self.logger.info("Conversation history cleared")
    
    async def cleanup(self) -> None:
        """Cleanup component resources."""
        if self._client:
            await self._client.close()
        await super().cleanup()
        self.logger.info("OpenAI Chat component cleaned up")