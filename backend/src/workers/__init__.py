"""
Worker system for executing flow nodes
"""

from .base_worker import BaseWorker, ExecutionContext
from .registry import NodeRegistry
from .worker_pool import WorkerPool

# Global registry instance
node_registry = NodeRegistry()

# Import and register all workers
from .input_worker import InputWorker
from .output_worker import OutputWorker
from .transform_worker import TransformWorker
from .condition_worker import ConditionWorker
from .api_worker import ApiWorker
from .database_worker import DatabaseWorker
from .ai_workers import OpenAIWorker, AnthropicWorker, OllamaWorker
from .template_worker import TemplateWorker
from .function_worker import FunctionWorker

# Register workers
node_registry.register('input', InputWorker())
node_registry.register('output', OutputWorker())
node_registry.register('transform', TransformWorker())
node_registry.register('condition', ConditionWorker())
node_registry.register('api', ApiWorker())
node_registry.register('database', DatabaseWorker())
node_registry.register('openai', OpenAIWorker())
node_registry.register('anthropic', AnthropicWorker())
node_registry.register('ollama', OllamaWorker())
node_registry.register('template', TemplateWorker())
node_registry.register('function', FunctionWorker())

# Note: Previously registered 'custom' type as alias for ConditionWorker
# This is no longer needed as the node type parsing has been fixed to use data.type

def initialize_workers():
    """Initialize all workers - already done during module import"""
    pass

def get_worker(node_type: str):
    """Get worker for a specific node type"""
    return node_registry.get_executor(node_type)

__all__ = ['BaseWorker', 'ExecutionContext', 'NodeRegistry', 'WorkerPool', 'node_registry', 'initialize_workers', 'get_worker']