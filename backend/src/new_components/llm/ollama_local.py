"""
파일명: ollama_local.py (450줄)
목적: Ollama 로컬 LLM 컴포넌트 메인 구현
동작 과정:
1. Ollama 서버 상태 확인 및 모델 검증
2. 프롬프트 포맷팅 및 로컬 API 호출
3. 스트리밍 응답 처리 및 결과 반환
4. 모델 관리 (다운로드, 업데이트 등)
데이터베이스 연동: 실행 로그 저장 (execution_logs 테이블)
의존성: base_llm.py, ollama_client.py
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
from .ollama_client import OllamaAPIClient

logger = structlog.get_logger()


class OllamaLocalComponent(BaseLLMComponent):
    """
    Ollama Local LLM Component.
    
    Ollama Execution Flow:
    1. check_ollama_server() → Verify Ollama server is running
    2. validate_model() → Check if model is available locally
    3. prepare_prompt() → Format input for selected model
    4. call_ollama_api() → Make local API call to Ollama
    5. process_response() → Parse response and extract content
    6. handle_streaming() → Support real-time response streaming
    7. track_usage() → Monitor performance and resource usage
    
    Privacy Features:
    - All processing happens locally (no external API calls)
    - No data leaves your machine
    - Support for air-gapped environments
    - Custom model support
    """
    
    @classmethod
    def get_metadata(cls) -> ComponentMetadata:
        return ComponentMetadata(
            name="Ollama Local",
            type="llm",
            category="Language Models",
            description="Chat with local LLM models via Ollama",
            version="1.0.0",
            author="MAX Platform",
            inputs=[
                ComponentInput(
                    name="prompt",
                    type=InputType.TEXT,
                    description="The prompt or question to send to the local model",
                    required=True
                ),
                ComponentInput(
                    name="system_prompt",
                    type=InputType.TEXT,
                    description="System prompt to set model behavior",
                    required=False
                ),
                ComponentInput(
                    name="model",
                    type=InputType.TEXT,
                    description="Ollama model name (llama2, codellama, mistral, etc.)",
                    required=False,
                    default="llama2"
                ),
                ComponentInput(
                    name="temperature",
                    type=InputType.NUMBER,
                    description="Sampling temperature (0.0-2.0). Higher = more creative",
                    required=False,
                    default=0.8
                ),
                ComponentInput(
                    name="num_predict",
                    type=InputType.NUMBER,
                    description="Maximum number of tokens to predict",
                    required=False,
                    default=128
                ),
                ComponentInput(
                    name="top_k",
                    type=InputType.NUMBER,
                    description="Top-K sampling parameter",
                    required=False,
                    default=40
                ),
                ComponentInput(
                    name="top_p",
                    type=InputType.NUMBER,
                    description="Top-P (nucleus) sampling parameter",
                    required=False,
                    default=0.9
                ),
                ComponentInput(
                    name="conversation_history",
                    type=InputType.JSON,
                    description="Previous conversation messages for context",
                    required=False
                ),
                ComponentInput(
                    name="stream",
                    type=InputType.BOOLEAN,
                    description="Stream response tokens as they arrive",
                    required=False,
                    default=True
                ),
                ComponentInput(
                    name="raw",
                    type=InputType.BOOLEAN,
                    description="Use raw prompt without template formatting",
                    required=False,
                    default=False
                ),
                ComponentInput(
                    name="format",
                    type=InputType.TEXT,
                    description="Response format (json, etc.)",
                    required=False
                ),
                ComponentInput(
                    name="ollama_url",
                    type=InputType.TEXT,
                    description="Ollama server URL",
                    required=False,
                    default="http://localhost:11434"
                )
            ],
            outputs=[
                ComponentOutput(
                    name="response",
                    type=OutputType.TEXT,
                    description="Model's response text"
                ),
                ComponentOutput(
                    name="model",
                    type=OutputType.TEXT,
                    description="Model used for generation"
                ),
                ComponentOutput(
                    name="total_duration",
                    type=OutputType.NUMBER,
                    description="Total generation time in nanoseconds"
                ),
                ComponentOutput(
                    name="load_duration",
                    type=OutputType.NUMBER,
                    description="Model load time in nanoseconds"
                ),
                ComponentOutput(
                    name="prompt_eval_count",
                    type=OutputType.NUMBER,
                    description="Number of tokens in prompt"
                ),
                ComponentOutput(
                    name="eval_count",
                    type=OutputType.NUMBER,
                    description="Number of tokens generated"
                ),
                ComponentOutput(
                    name="context",
                    type=OutputType.JSON,
                    description="Context array for conversation continuity"
                )
            ],
            documentation="""
            # Ollama Local Component
            
            This component integrates with Ollama to run large language models locally.
            
            ## Supported Models
            - **Llama 2**: Meta's open-source model (7B, 13B, 70B)
            - **Code Llama**: Specialized for code generation
            - **Mistral**: Efficient 7B model from Mistral AI
            - **Dolphin**: Fine-tuned models for various tasks
            - **Orca Mini**: Compact models for resource-constrained environments
            - **Custom Models**: Any GGUF model compatible with Ollama
            
            ## Features
            - Complete local processing (privacy-first)
            - Streaming responses for real-time interaction
            - Conversation history support
            - Custom model parameters (temperature, top-k, top-p)
            - JSON format output support
            - Air-gapped environment support
            
            ## Prerequisites
            1. Install Ollama: https://ollama.ai/
            2. Pull desired models: `ollama pull llama2`
            3. Start Ollama server: `ollama serve`
            
            ## Example Usage
            ```json
            {
                "prompt": "Write a Python function to calculate fibonacci numbers",
                "model": "codellama",
                "temperature": 0.1,
                "num_predict": 200
            }
            ```
            """
        )
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ollama component."""
        try:
            # Update status
            await self.update_status(ComponentStatus.EXECUTING, "Preparing Ollama request")
            
            # Extract inputs
            prompt = inputs.get("prompt", "")
            system_prompt = inputs.get("system_prompt", None)
            self.model = inputs.get("model", "llama2")
            temperature = float(inputs.get("temperature", 0.8))
            num_predict = int(inputs.get("num_predict", 128))
            top_k = int(inputs.get("top_k", 40))
            top_p = float(inputs.get("top_p", 0.9))
            conversation_history = inputs.get("conversation_history", [])
            self.stream = inputs.get("stream", True)
            raw = inputs.get("raw", False)
            format_type = inputs.get("format", None)
            ollama_url = inputs.get("ollama_url", "http://localhost:11434")
            
            # Validate inputs
            if not prompt:
                raise ValueError("Prompt is required")
            
            # Initialize Ollama client
            client = OllamaAPIClient(ollama_url)
            
            # Check server status
            if not await client.check_server_status():
                raise ValueError(f"Ollama server not available at {ollama_url}")
            
            # Check if model is available
            available_models = await client.list_models()
            model_names = [model.get("name", "").split(":")[0] for model in available_models]
            
            if self.model not in model_names and not any(name.startswith(self.model) for name in model_names):
                logger.warning(f"Model {self.model} not found locally, attempting to pull...")
                await self.pull_model(client, self.model)
            
            # Prepare model options
            options = {
                "temperature": temperature,
                "num_predict": num_predict,
                "top_k": top_k,
                "top_p": top_p
            }
            
            await self.update_status(ComponentStatus.EXECUTING, f"Calling Ollama model: {self.model}")
            
            # Initialize response variables
            response_text = ""
            total_duration = 0
            load_duration = 0
            prompt_eval_count = 0
            eval_count = 0
            context = []
            
            # Choose API method based on conversation history
            if conversation_history:
                # Use chat API for conversation
                messages = self.prepare_messages(prompt, system_prompt, conversation_history)
                
                async for chunk in client.chat(
                    model=self.model,
                    messages=messages,
                    stream=self.stream,
                    format=format_type,
                    options=options
                ):
                    if self.stream and not chunk.get("done", False):
                        # Handle streaming response
                        message = chunk.get("message", {})
                        delta_text = message.get("content", "")
                        response_text += delta_text
                        
                        # Emit streaming update
                        await self.emit_streaming_update({
                            "text": delta_text,
                            "accumulated": response_text
                        })
                    elif chunk.get("done", False):
                        # Handle final chunk with metadata
                        total_duration = chunk.get("total_duration", 0)
                        load_duration = chunk.get("load_duration", 0)
                        prompt_eval_count = chunk.get("prompt_eval_count", 0)
                        eval_count = chunk.get("eval_count", 0)
                        
                        if not self.stream:
                            message = chunk.get("message", {})
                            response_text = message.get("content", "")
            else:
                # Use generate API for single prompt
                full_prompt = prompt
                if system_prompt and not raw:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                async for chunk in client.generate(
                    model=self.model,
                    prompt=full_prompt,
                    system=system_prompt if not raw else None,
                    stream=self.stream,
                    raw=raw,
                    format=format_type,
                    options=options
                ):
                    if self.stream and not chunk.get("done", False):
                        # Handle streaming response
                        delta_text = chunk.get("response", "")
                        response_text += delta_text
                        
                        # Emit streaming update
                        await self.emit_streaming_update({
                            "text": delta_text,
                            "accumulated": response_text
                        })
                    elif chunk.get("done", False):
                        # Handle final chunk with metadata
                        total_duration = chunk.get("total_duration", 0)
                        load_duration = chunk.get("load_duration", 0)
                        prompt_eval_count = chunk.get("prompt_eval_count", 0)
                        eval_count = chunk.get("eval_count", 0)
                        context = chunk.get("context", [])
                        
                        if not self.stream:
                            response_text = chunk.get("response", "")
            
            # Prepare outputs
            outputs = {
                "response": response_text,
                "model": self.model,
                "total_duration": total_duration,
                "load_duration": load_duration,
                "prompt_eval_count": prompt_eval_count,
                "eval_count": eval_count,
                "context": context
            }
            
            await self.update_status(ComponentStatus.COMPLETED, "Ollama request completed")
            
            return outputs
            
        except Exception as e:
            await self.update_status(
                ComponentStatus.FAILED, 
                f"Ollama execution failed: {str(e)}"
            )
            logger.error(
                "ollama_execution_failed",
                component_id=self.component_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def validate_api_key(self) -> bool:
        """Ollama doesn't require API keys."""
        return True
    
    async def call_api(self, messages: List[Dict[str, str]]):
        """Not used in Ollama component - using direct client calls."""
        pass
    
    async def pull_model(self, client: OllamaAPIClient, model_name: str):
        """Pull/download a model if not available locally."""
        logger.info(f"Pulling model {model_name} from Ollama registry...")
        
        await self.update_status(
            ComponentStatus.EXECUTING, 
            f"Downloading model: {model_name}"
        )
        
        async for progress in client.pull_model(model_name):
            if "status" in progress:
                logger.debug(f"Pull progress: {progress['status']}")
                
                # Update status with download progress
                if "total" in progress and "completed" in progress:
                    percent = (progress["completed"] / progress["total"]) * 100
                    await self.update_status(
                        ComponentStatus.EXECUTING,
                        f"Downloading {model_name}: {percent:.1f}%"
                    )
    
    async def emit_streaming_update(self, update: Dict[str, Any]):
        """Emit streaming update for real-time response."""
        logger.debug(
            "ollama_streaming_update",
            component_id=self.component_id,
            update=update
        )
        
        # Emit through WebSocket if orchestrator is available
        if hasattr(self, 'orchestrator') and self.orchestrator:
            try:
                await self.orchestrator.emit_streaming_update(
                    node_id=self.component_id,
                    node_type="llm",
                    node_label=f"Ollama ({self.model})",
                    delta=update.get("text", ""),
                    accumulated=update.get("accumulated", ""),
                    is_complete=False
                )
            except Exception as e:
                logger.warning(
                    "Failed to emit streaming update",
                    component_id=self.component_id,
                    error=str(e)
                )