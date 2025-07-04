"""
AI Node Workers (OpenAI and Anthropic)
"""

import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from .base_worker import BaseWorker, ExecutionContext
from ..new_components.llm.ollama_client import OllamaAPIClient


class OpenAIWorker(BaseWorker):
    """Worker for OpenAI API calls"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Call OpenAI API
        """
        self.logger.info("Executing OpenAI node", node_id=context.node_id)
        
        if not self.client:
            return self.format_output(
                response=None,
                tokens=0,
                error="OpenAI API key not configured"
            )
        
        # Get configuration
        model = config.get('model', 'gpt-3.5-turbo')
        base_prompt = config.get('prompt', '')
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 1000))
        
        # Get inputs - check multiple possible input field names
        prompt = inputs.get('message', inputs.get('prompt', base_prompt))
        context_text = inputs.get('context', '')
        
        if not prompt:
            raise ValueError("Prompt is required")
        
        # Build full prompt with context
        full_prompt = prompt
        if context_text:
            full_prompt = f"Context: {context_text}\n\n{prompt}"
        
        try:
            # Call OpenAI API
            self.logger.info(
                "Calling OpenAI API",
                node_id=context.node_id,
                model=model
            )
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            self.logger.info(
                "OpenAI API call completed",
                node_id=context.node_id,
                tokens_used=tokens_used
            )
            
            return self.format_output(
                response=response_text,
                tokens=tokens_used,
                error=None
            )
            
        except Exception as e:
            self.logger.error(
                "OpenAI API call failed",
                node_id=context.node_id,
                error=str(e)
            )
            return self.format_output(
                response=None,
                tokens=0,
                error=str(e)
            )


class AnthropicWorker(BaseWorker):
    """Worker for Anthropic API calls"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Call Anthropic API
        """
        self.logger.info("Executing Anthropic node", node_id=context.node_id)
        
        if not self.client:
            return self.format_output(
                response=None,
                tokens=0,
                error="Anthropic API key not configured"
            )
        
        # Get configuration
        model = config.get('model', 'claude-3-haiku-20240307')
        base_prompt = config.get('prompt', '')
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 1000))
        
        # Get inputs - check multiple possible input field names
        prompt = inputs.get('message', inputs.get('prompt', base_prompt))
        context_text = inputs.get('context', '')
        
        if not prompt:
            raise ValueError("Prompt is required")
        
        # Build full prompt with context
        full_prompt = prompt
        if context_text:
            full_prompt = f"Context: {context_text}\n\n{prompt}"
        
        try:
            # Call Anthropic API
            self.logger.info(
                "Calling Anthropic API",
                node_id=context.node_id,
                model=model
            )
            
            response = await self.client.messages.create(
                model=model,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response
            response_text = response.content[0].text if response.content else ""
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            self.logger.info(
                "Anthropic API call completed",
                node_id=context.node_id,
                tokens_used=tokens_used
            )
            
            return self.format_output(
                response=response_text,
                tokens=tokens_used,
                error=None
            )
            
        except Exception as e:
            self.logger.error(
                "Anthropic API call failed",
                node_id=context.node_id,
                error=str(e)
            )
            return self.format_output(
                response=None,
                tokens=0,
                error=str(e)
            )


class OllamaWorker(BaseWorker):
    """Worker for Ollama local LLM calls"""
    
    def __init__(self):
        super().__init__()
        self.client = OllamaAPIClient()
        self.orchestrator = None  # Will be set by InteractiveOrchestrator
    
    def set_orchestrator(self, orchestrator):
        """Set the orchestrator for streaming callbacks"""
        self.orchestrator = orchestrator
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Call Ollama local API
        """
        self.logger.info("Executing Ollama node", node_id=context.node_id)
        
        # Check server status first
        server_status = await self.client.check_server_status()
        if not server_status:
            return {
                'response': None,
                'tokens': 0,
                'error': "Ollama server not running. Please start Ollama service."
            }
        
        # Get configuration
        model = config.get('model', 'llama2')
        base_prompt = config.get('prompt', '')
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 1000))
        stream = config.get('stream', True)  # Enable streaming by default
        
        # Get inputs - check multiple possible input field names
        prompt = inputs.get('message', inputs.get('prompt', base_prompt))
        context_text = inputs.get('context', '')
        
        if not prompt:
            raise ValueError("Prompt is required")
        
        # Build full prompt with context
        full_prompt = prompt
        if context_text:
            full_prompt = f"Context: {context_text}\n\n{prompt}"
        
        try:
            # Check if model exists, pull if needed
            models = await self.client.list_models()
            model_names = [m['name'] for m in models]
            
            if model not in model_names:
                self.logger.info(
                    "Model not found, pulling from registry",
                    node_id=context.node_id,
                    model=model
                )
                await self.client.pull_model(model)
            
            # Call Ollama API
            self.logger.info(
                "Calling Ollama API",
                node_id=context.node_id,
                model=model
            )
            
            # Use generate API for text completion
            response_text = ""
            tokens_used = 0
            
            async for chunk in self.client.generate(
                model=model,
                prompt=full_prompt,
                stream=stream,  # Use streaming configuration
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            ):
                if stream and not chunk.get('done', False):
                    # Handle streaming response
                    delta_text = chunk.get('response', '')
                    if delta_text:
                        response_text += delta_text
                        
                        # Emit streaming update if orchestrator is available
                        if self.orchestrator:
                            try:
                                await self.orchestrator.emit_streaming_update(
                                    node_id=context.node_id,
                                    node_type="ollama",
                                    node_label=f"Ollama ({model})",
                                    delta=delta_text,
                                    accumulated=response_text,
                                    is_complete=False
                                )
                            except Exception as e:
                                self.logger.warning(
                                    "Failed to emit streaming update",
                                    node_id=context.node_id,
                                    error=str(e)
                                )
                elif chunk.get('done', False):
                    # Handle final chunk with metadata
                    tokens_used = chunk.get('eval_count', 0) + chunk.get('prompt_eval_count', 0)
                    if not stream:
                        response_text = chunk.get('response', '')
                    
                    # Emit final streaming update to signal completion
                    if stream and self.orchestrator:
                        try:
                            await self.orchestrator.emit_streaming_update(
                                node_id=context.node_id,
                                node_type="ollama",
                                node_label=f"Ollama ({model})",
                                delta="",
                                accumulated=response_text,
                                is_complete=True
                            )
                        except Exception as e:
                            self.logger.warning(
                                "Failed to emit final streaming update",
                                node_id=context.node_id,
                                error=str(e)
                            )
                    break
            
            self.logger.info(
                "Ollama API call completed",
                node_id=context.node_id,
                tokens_used=tokens_used
            )
            
            return {
                'response': response_text,
                'tokens': tokens_used,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(
                "Ollama API call failed",
                node_id=context.node_id,
                error=str(e)
            )
            return {
                'response': None,
                'tokens': 0,
                'error': str(e)
            }