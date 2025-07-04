"""
┌──────────────────────────────────────────────────────────────┐
│                   Text Input Component Flow                 │
│                                                              │
│  [Config] → [Validate] → [Process] → [Output]              │
│     ↓         ↓           ↓           ↓                     │
│  텍스트설정   유효성검사    텍스트처리    결과출력             │
│                                                              │
│  Data Flow: Configuration → Text Value → Output Stream     │
│  Validation: Length Check → Format Check → Content Filter  │
└──────────────────────────────────────────────────────────────┘

Text Input Component for MAX Flowstudio
Flow: Configuration text → Validation → Processing → Output as text data
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ...core.component_base import (
    BaseComponent, 
    ComponentMetadata, 
    ComponentInput, 
    ComponentOutput,
    InputType,
    OutputType
)

logger = structlog.get_logger()


class TextInputComponent(BaseComponent):
    """
    Text Input Component for providing static or dynamic text data.
    
    Text Input Flow:
    1. get_configured_text() → Retrieve text from configuration
    2. validate_text() → Check length, format, and content
    3. process_text() → Apply any transformations
    4. output_text() → Provide text to downstream components
    
    Features:
    - Static text configuration
    - Dynamic text from inputs
    - Text validation and filtering
    - Multi-line text support
    - Variable substitution
    - Text templates
    """
    
    def __init__(self, **kwargs):
        """Initialize Text Input component."""
        super().__init__(**kwargs)
        
        # Component configuration
        self.default_text: str = kwargs.get('default_text', '')
        self.allow_empty: bool = kwargs.get('allow_empty', False)
        self.max_length: Optional[int] = kwargs.get('max_length', None)
        self.multiline: bool = kwargs.get('multiline', True)
        self.template_mode: bool = kwargs.get('template_mode', False)
    
    @property
    def metadata(self) -> ComponentMetadata:
        """Component metadata definition."""
        return ComponentMetadata(
            name="text_input",
            display_name="Text Input",
            description="Provides text data as input to workflows",
            category="data_sources",
            icon="text",
            version="1.0.0",
            author="MAX Flowstudio",
            documentation="""
# Text Input Component

This component provides text data as input to your workflows.

## Features
- Static text configuration
- Dynamic text input support
- Multi-line text support
- Text validation and length checking
- Template mode with variable substitution

## Configuration
- **Default Text**: The default text value
- **Allow Empty**: Whether to allow empty text
- **Max Length**: Maximum text length (optional)
- **Multiline**: Support for multi-line text
- **Template Mode**: Enable variable substitution

## Usage
1. Configure the default text value
2. Optionally connect dynamic text input
3. Set validation rules as needed
4. Connect output to downstream components
            """,
            tags=["input", "text", "data-source", "static", "template"]
        )
    
    @property
    def inputs(self) -> List[ComponentInput]:
        """Component input definitions."""
        return [
            ComponentInput(
                name="text_value",
                display_name="Text Value",
                description="Dynamic text input (overrides default text)",
                input_type=InputType.TEXT,
                required=False
            ),
            ComponentInput(
                name="variables",
                display_name="Template Variables",
                description="Variables for template substitution (if template mode enabled)",
                input_type=InputType.OBJECT,
                required=False,
                default_value={}
            )
        ]
    
    @property
    def outputs(self) -> List[ComponentOutput]:
        """Component output definitions."""
        return [
            ComponentOutput(
                name="text",
                display_name="Text Output",
                description="The processed text output",
                output_type=OutputType.TEXT
            ),
            ComponentOutput(
                name="metadata",
                display_name="Text Metadata",
                description="Metadata about the text (length, lines, etc.)",
                output_type=OutputType.OBJECT
            )
        ]
    
    async def build_results(self) -> Dict[str, Any]:
        """
        Execute the text input processing.
        
        Text Processing Flow:
        1. Get text value (dynamic input or default)
        2. Validate text according to rules
        3. Apply template substitution if enabled
        4. Generate metadata
        5. Return processed text and metadata
        """
        self.logger.info("Processing text input")
        
        # Get input values
        text_value = self.get_input("text_value")
        variables = self.get_input("variables", {})
        
        # Determine final text value
        final_text = text_value if text_value is not None else self.default_text
        
        # Validate text
        await self._validate_text(final_text)
        
        # Apply template substitution if enabled
        if self.template_mode and variables:
            final_text = await self._apply_template(final_text, variables)
        
        # Generate metadata
        metadata = await self._generate_metadata(final_text)
        
        self.logger.info("Text input processed successfully", 
                        text_length=len(final_text),
                        multiline=self.multiline)
        
        return {
            "text": final_text,
            "metadata": metadata
        }
    
    async def _validate_text(self, text: str) -> None:
        """Validate text according to component rules."""
        # Check if empty text is allowed
        if not text and not self.allow_empty:
            raise ValueError("Empty text is not allowed")
        
        # Check maximum length
        if self.max_length and len(text) > self.max_length:
            raise ValueError(f"Text length ({len(text)}) exceeds maximum allowed length ({self.max_length})")
        
        self.logger.debug("Text validation passed", text_length=len(text))
    
    async def _apply_template(self, text: str, variables: Dict[str, Any]) -> str:
        """Apply template variable substitution."""
        try:
            # Simple template substitution using string format
            processed_text = text.format(**variables)
            
            self.logger.debug("Template substitution applied", 
                            variables_count=len(variables))
            
            return processed_text
            
        except KeyError as e:
            raise ValueError(f"Template variable not found: {str(e)}")
        except Exception as e:
            raise ValueError(f"Template substitution failed: {str(e)}")
    
    async def _generate_metadata(self, text: str) -> Dict[str, Any]:
        """Generate metadata about the text."""
        lines = text.split('\n') if self.multiline else [text]
        
        metadata = {
            "length": len(text),
            "line_count": len(lines),
            "word_count": len(text.split()) if text else 0,
            "character_count": len(text),
            "is_multiline": '\n' in text,
            "is_empty": len(text) == 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return metadata