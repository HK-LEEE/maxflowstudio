"""
┌─────────────────────────────────────────────────────────────┐
│                   Component Process Flow                    │
│                                                             │
│  [Request] → [Validate] → [Execute] → [Cache] → [Response]  │
│      ↓           ↓           ↓          ↓          ↓        │
│   입력검증    타입체크     비즈니스로직   결과저장    출력반환    │
│                                                             │
│  Data Flow: Input → Process → Output → Next Component      │
│                                                             │
│  Error Handling: Validate → Fail → Log → Propagate         │
│  Async Flow: Queue → Schedule → Execute → Monitor → Done   │
└─────────────────────────────────────────────────────────────┘

Base Component System for MAX Flowstudio
Flow: Component initialization → Input validation → Execution → Output generation
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from enum import Enum
import asyncio
import structlog
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger()

T = TypeVar('T')


class ComponentStatus(str, Enum):
    """Component execution status."""
    IDLE = "idle"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InputType(str, Enum):
    """Input data types for components."""
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE = "file"
    JSON = "json"
    ANY = "any"


class OutputType(str, Enum):
    """Output data types for components."""
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE = "file"
    JSON = "json"
    STREAM = "stream"
    ANY = "any"


class ComponentInput(BaseModel):
    """Component input definition."""
    name: str = Field(..., description="Input parameter name")
    display_name: str = Field(..., description="Human-readable input name")
    description: str = Field(..., description="Input description")
    input_type: InputType = Field(..., description="Input data type")
    required: bool = Field(default=True, description="Whether input is required")
    default_value: Any = Field(default=None, description="Default value")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.isidentifier():
            raise ValueError("Input name must be a valid Python identifier")
        return v


class ComponentOutput(BaseModel):
    """Component output definition."""
    name: str = Field(..., description="Output parameter name")
    display_name: str = Field(..., description="Human-readable output name")
    description: str = Field(..., description="Output description")
    output_type: OutputType = Field(..., description="Output data type")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.isidentifier():
            raise ValueError("Output name must be a valid Python identifier")
        return v


class ComponentMetadata(BaseModel):
    """Component metadata definition."""
    name: str = Field(..., description="Component name")
    display_name: str = Field(..., description="Human-readable component name")
    description: str = Field(..., description="Component description")
    category: str = Field(..., description="Component category")
    icon: str = Field(default="component", description="Component icon")
    version: str = Field(default="1.0.0", description="Component version")
    author: str = Field(default="MAX Flowstudio", description="Component author")
    documentation: str = Field(default="", description="Component documentation")
    tags: List[str] = Field(default_factory=list, description="Component tags")


class ComponentConfig(BaseModel):
    """Component configuration."""
    timeout_seconds: int = Field(default=300, description="Execution timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    cache_results: bool = Field(default=True, description="Whether to cache results")
    async_execution: bool = Field(default=True, description="Whether to execute asynchronously")
    log_level: str = Field(default="INFO", description="Logging level")


class ComponentResult(BaseModel):
    """Component execution result."""
    component_id: str = Field(..., description="Component instance ID")
    execution_id: str = Field(..., description="Execution ID")
    status: ComponentStatus = Field(..., description="Execution status")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output values")
    execution_time: float = Field(..., description="Execution time in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    logs: List[str] = Field(default_factory=list, description="Execution logs")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class BaseComponent(ABC):
    """
    Base class for all workflow components.
    
    Component Lifecycle:
    1. __init__() → Component initialization and metadata setup
    2. validate_inputs() → Input data validation and type checking
    3. build_results() → Core business logic execution
    4. cache_results() → Result caching and state update
    5. get_outputs() → Output data preparation for next components
    
    Data Flow:
    Input Data → Validation → Processing → Output → Next Component
    
    Error Handling:
    Validation Error → Log → Propagate → Stop Execution
    Runtime Error → Retry → Fallback → Log → Propagate
    """
    
    def __init__(self, **kwargs):
        """Initialize component with configuration."""
        self.id = str(uuid.uuid4())
        self.config = ComponentConfig(**kwargs.get('config', {}))
        self.status = ComponentStatus.IDLE
        self.logger = logger.bind(component_id=self.id, component_name=self.__class__.__name__)
        
        # Internal state
        self._inputs: Dict[str, Any] = {}
        self._outputs: Dict[str, Any] = {}
        self._execution_context: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        self._execution_start_time: Optional[datetime] = None
        self._execution_end_time: Optional[datetime] = None
        self._current_execution_id: Optional[str] = None
        
        self.logger.info("Component initialized", component_id=self.id)
    
    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Component metadata - must be implemented by subclasses."""
        pass
    
    @property
    @abstractmethod
    def inputs(self) -> List[ComponentInput]:
        """Component input definitions - must be implemented by subclasses."""
        pass
    
    @property
    @abstractmethod
    def outputs(self) -> List[ComponentOutput]:
        """Component output definitions - must be implemented by subclasses."""
        pass
    
    def set_inputs(self, inputs: Dict[str, Any]) -> None:
        """Set input values for the component."""
        self._inputs = inputs.copy()
        self.logger.debug("Inputs set", inputs=list(inputs.keys()))
    
    def get_input(self, name: str, default: Any = None) -> Any:
        """Get input value by name."""
        return self._inputs.get(name, default)
    
    def set_output(self, name: str, value: Any) -> None:
        """Set output value."""
        self._outputs[name] = value
        self.logger.debug("Output set", output_name=name, output_type=type(value).__name__)
    
    def get_output(self, name: str, default: Any = None) -> Any:
        """Get output value by name."""
        return self._outputs.get(name, default)
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """Get all output values."""
        return self._outputs.copy()
    
    async def validate_inputs(self) -> bool:
        """
        Validate input data against component requirements.
        
        Validation Flow:
        1. Check required inputs are present
        2. Validate data types
        3. Apply validation rules
        4. Log validation results
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        self.status = ComponentStatus.VALIDATING
        self.logger.info("Starting input validation")
        
        try:
            # Check required inputs
            for input_def in self.inputs:
                if input_def.required and input_def.name not in self._inputs:
                    if input_def.default_value is not None:
                        self._inputs[input_def.name] = input_def.default_value
                        self.logger.debug("Applied default value", 
                                        input_name=input_def.name, 
                                        default_value=input_def.default_value)
                    else:
                        self.logger.error("Required input missing", input_name=input_def.name)
                        return False
            
            # Validate data types and rules
            for input_def in self.inputs:
                if input_def.name in self._inputs:
                    value = self._inputs[input_def.name]
                    if not await self._validate_input_value(input_def, value):
                        return False
            
            self.logger.info("Input validation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Input validation failed", error=str(e))
            return False
    
    async def _validate_input_value(self, input_def: ComponentInput, value: Any) -> bool:
        """Validate a single input value."""
        try:
            # Type validation
            if not self._check_input_type(input_def.input_type, value):
                self.logger.error("Input type validation failed", 
                                input_name=input_def.name,
                                expected_type=input_def.input_type,
                                actual_type=type(value).__name__)
                return False
            
            # Apply validation rules
            for rule_name, rule_value in input_def.validation_rules.items():
                if not await self._apply_validation_rule(rule_name, rule_value, value):
                    self.logger.error("Validation rule failed", 
                                    input_name=input_def.name,
                                    rule=rule_name,
                                    rule_value=rule_value)
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Input value validation error", 
                            input_name=input_def.name, 
                            error=str(e))
            return False
    
    def _check_input_type(self, expected_type: InputType, value: Any) -> bool:
        """Check if value matches expected input type."""
        if expected_type == InputType.ANY:
            return True
        
        type_mapping = {
            InputType.TEXT: str,
            InputType.NUMBER: (int, float),
            InputType.BOOLEAN: bool,
            InputType.ARRAY: list,
            InputType.OBJECT: dict,
            InputType.JSON: (dict, list),
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True
    
    async def _apply_validation_rule(self, rule_name: str, rule_value: Any, value: Any) -> bool:
        """Apply a specific validation rule."""
        if rule_name == "min_length" and isinstance(value, str):
            return len(value) >= rule_value
        elif rule_name == "max_length" and isinstance(value, str):
            return len(value) <= rule_value
        elif rule_name == "min_value" and isinstance(value, (int, float)):
            return value >= rule_value
        elif rule_name == "max_value" and isinstance(value, (int, float)):
            return value <= rule_value
        elif rule_name == "pattern" and isinstance(value, str):
            import re
            return bool(re.match(rule_value, value))
        
        return True
    
    @abstractmethod
    async def build_results(self) -> Dict[str, Any]:
        """
        Core component logic - must be implemented by subclasses.
        
        Execution Flow:
        1. Access validated inputs via self.get_input()
        2. Perform component-specific processing
        3. Generate outputs
        4. Return results dictionary
        
        Returns:
            Dict[str, Any]: Component execution results
        """
        pass
    
    async def execute(self, inputs: Dict[str, Any], execution_id: Optional[str] = None) -> ComponentResult:
        """
        Execute the component with given inputs.
        
        Complete Execution Flow:
        1. Set inputs and execution context
        2. Validate inputs
        3. Execute core logic
        4. Cache results if enabled
        5. Return execution result
        
        Args:
            inputs: Input data dictionary
            execution_id: Optional execution identifier
            
        Returns:
            ComponentResult: Execution result with outputs and metadata
        """
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        self._current_execution_id = execution_id
        self._execution_start_time = datetime.utcnow()
        
        self.logger.info("Starting component execution", execution_id=execution_id)
        
        try:
            # Set inputs
            self.set_inputs(inputs)
            
            # Validate inputs
            if not await self.validate_inputs():
                self.status = ComponentStatus.FAILED
                return ComponentResult(
                    component_id=self.id,
                    execution_id=execution_id,
                    status=self.status,
                    execution_time=0.0,
                    error_message="Input validation failed"
                )
            
            # Execute core logic
            self.status = ComponentStatus.EXECUTING
            self.logger.info("Executing component logic")
            
            # Apply timeout
            try:
                results = await asyncio.wait_for(
                    self.build_results(),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                self.status = ComponentStatus.FAILED
                error_msg = f"Component execution timed out after {self.config.timeout_seconds} seconds"
                self.logger.error(error_msg)
                return ComponentResult(
                    component_id=self.id,
                    execution_id=execution_id,
                    status=self.status,
                    execution_time=self.config.timeout_seconds,
                    error_message=error_msg
                )
            
            # Process results
            if isinstance(results, dict):
                self._outputs.update(results)
            
            # Cache results if enabled
            if self.config.cache_results:
                await self._cache_results(execution_id, results)
            
            self.status = ComponentStatus.COMPLETED
            self._execution_end_time = datetime.utcnow()
            execution_time = (self._execution_end_time - self._execution_start_time).total_seconds()
            
            self.logger.info("Component execution completed successfully", 
                           execution_time=execution_time)
            
            return ComponentResult(
                component_id=self.id,
                execution_id=execution_id,
                status=self.status,
                outputs=self.get_all_outputs(),
                execution_time=execution_time
            )
            
        except Exception as e:
            self.status = ComponentStatus.FAILED
            self._execution_end_time = datetime.utcnow()
            execution_time = (self._execution_end_time - self._execution_start_time).total_seconds()
            
            error_msg = f"Component execution failed: {str(e)}"
            self.logger.error(error_msg, error=str(e), exc_info=True)
            
            return ComponentResult(
                component_id=self.id,
                execution_id=execution_id,
                status=self.status,
                execution_time=execution_time,
                error_message=error_msg
            )
    
    async def _cache_results(self, execution_id: str, results: Dict[str, Any]) -> None:
        """Cache execution results for future use."""
        cache_key = f"{self.id}:{execution_id}"
        self._cache[cache_key] = {
            "results": results,
            "timestamp": datetime.utcnow(),
            "execution_id": execution_id
        }
        self.logger.debug("Results cached", cache_key=cache_key)
    
    def get_cached_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result by execution ID."""
        cache_key = f"{self.id}:{execution_id}"
        cached_data = self._cache.get(cache_key)
        if cached_data:
            self.logger.debug("Cache hit", cache_key=cache_key)
            return cached_data["results"]
        return None
    
    async def cleanup(self) -> None:
        """Cleanup component resources."""
        self._inputs.clear()
        self._outputs.clear()
        self._execution_context.clear()
        self._cache.clear()
        self.status = ComponentStatus.IDLE
        self.logger.info("Component cleanup completed")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, status={self.status})>"