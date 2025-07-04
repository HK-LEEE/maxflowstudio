"""
LLM Node Executors
Flow: LLM Config -> API Call -> Response Processing
"""

import os
import asyncio
from typing import Dict, Any

import httpx
import structlog

from .base_worker import BaseNodeExecutor

logger = structlog.get_logger(__name__)


class OpenAIExecutor(BaseNodeExecutor):
    """Executor for OpenAI nodes."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate OpenAI configuration."""
        required_fields = ['model']
        return all(field in config for field in required_fields)
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OpenAI API call."""
        if not self.api_key:
            self.logger.warning("OpenAI API key not configured, using simulation")
            return await self._simulate_execution(config, inputs)
        
        model = config.get('model', 'gpt-3.5-turbo')
        prompt = config.get('prompt', 'Hello, world!')
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 1000))
        
        # Replace placeholders in prompt with input values
        formatted_prompt = self._format_prompt(prompt, inputs)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": formatted_prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return {
                    'response': content,
                    'model': model,
                    'usage': result.get('usage', {}),
                    'prompt': formatted_prompt
                }
                
        except Exception as e:
            self.logger.error("OpenAI API call failed", error=str(e))
            raise
    
    async def _simulate_execution(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate OpenAI execution when API key is not available."""
        model = config.get('model', 'gpt-3.5-turbo')
        prompt = config.get('prompt', 'Hello, world!')
        formatted_prompt = self._format_prompt(prompt, inputs)
        
        # Simulate processing time
        await asyncio.sleep(1.0)
        
        return {
            'response': f"[SIMULATED] OpenAI {model} response for: {formatted_prompt[:50]}...",
            'model': model,
            'usage': {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150},
            'prompt': formatted_prompt,
            'simulated': True
        }
    
    def _format_prompt(self, prompt: str, inputs: Dict[str, Any]) -> str:
        """Format prompt with input values."""
        formatted = prompt
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))
        return formatted


class AnthropicExecutor(BaseNodeExecutor):
    """Executor for Anthropic Claude nodes."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Anthropic configuration."""
        required_fields = ['model']
        return all(field in config for field in required_fields)
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Anthropic API call."""
        if not self.api_key:
            self.logger.warning("Anthropic API key not configured, using simulation")
            return await self._simulate_execution(config, inputs)
        
        model = config.get('model', 'claude-3-sonnet-20240229')
        prompt = config.get('prompt', 'Hello, world!')
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 1000))
        
        # Format prompt with inputs
        formatted_prompt = self._format_prompt(prompt, inputs)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": formatted_prompt}]
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                
                result = response.json()
                content = result['content'][0]['text']
                
                return {
                    'response': content,
                    'model': model,
                    'usage': result.get('usage', {}),
                    'prompt': formatted_prompt
                }
                
        except Exception as e:
            self.logger.error("Anthropic API call failed", error=str(e))
            raise
    
    async def _simulate_execution(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Anthropic execution when API key is not available."""
        model = config.get('model', 'claude-3-sonnet-20240229')
        prompt = config.get('prompt', 'Hello, world!')
        formatted_prompt = self._format_prompt(prompt, inputs)
        
        # Simulate processing time
        await asyncio.sleep(1.2)
        
        return {
            'response': f"[SIMULATED] Claude {model} response for: {formatted_prompt[:50]}...",
            'model': model,
            'usage': {'input_tokens': 50, 'output_tokens': 100},
            'prompt': formatted_prompt,
            'simulated': True
        }
    
    def _format_prompt(self, prompt: str, inputs: Dict[str, Any]) -> str:
        """Format prompt with input values."""
        formatted = prompt
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))
        return formatted