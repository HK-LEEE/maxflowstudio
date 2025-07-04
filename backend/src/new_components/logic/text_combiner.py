"""
┌──────────────────────────────────────────────────────────────┐
│                 Text Combiner Component Flow                │
│                                                              │
│  [Inputs] → [Combine] → [Format] → [Output]                │
│     ↓         ↓          ↓          ↓                       │
│  다중입력    텍스트결합   포맷적용     결과출력                │
│                                                              │
│  Data Flow: Multiple Texts → Combination Logic → Single Text │
│  Formatting: Separator → Template → Custom Format           │
└──────────────────────────────────────────────────────────────┘

Text Combiner Component for MAX Flowstudio
Flow: Multiple text inputs → Combination logic → Formatted output
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


class TextCombinerComponent(BaseComponent):
    """
    Text Combiner Component for combining multiple text inputs.
    
    Text Combination Flow:
    1. collect_inputs() → Gather all text inputs
    2. validate_inputs() → Check input validity
    3. apply_combination_logic() → Combine texts using specified method
    4. format_output() → Apply formatting and templates
    5. output_result() → Provide combined text
    
    Features:
    - Multiple text input support
    - Various combination methods (concatenate, join, template)
    - Custom separators and formatting
    - Template-based combination
    - Order preservation
    - Empty input handling
    """
    
    def __init__(self, **kwargs):
        """Initialize Text Combiner component."""
        super().__init__(**kwargs)
        
        # Component configuration
        self.combination_method: str = kwargs.get('combination_method', 'concatenate')
        self.separator: str = kwargs.get('separator', ' ')
        self.template: Optional[str] = kwargs.get('template', None)
        self.ignore_empty: bool = kwargs.get('ignore_empty', True)
        self.preserve_order: bool = kwargs.get('preserve_order', True)
    
    @property
    def metadata(self) -> ComponentMetadata:
        """Component metadata definition."""
        return ComponentMetadata(
            name="text_combiner",
            display_name="Text Combiner",
            description="Combines multiple text inputs into a single output",
            category="logic",
            icon="combine",
            version="1.0.0",
            author="MAX Flowstudio",
            documentation="""
# Text Combiner Component

This component combines multiple text inputs into a single text output.

## Features
- Multiple text input support
- Various combination methods (concatenate, join, template)
- Custom separators and delimiters
- Template-based combination with placeholders
- Option to ignore empty inputs
- Order preservation

## Combination Methods
- **Concatenate**: Simply join texts together
- **Join**: Join texts with a separator
- **Template**: Use a template with placeholders
- **List**: Create a formatted list

## Configuration
- **Method**: How to combine the texts
- **Separator**: Text to place between inputs (for join method)
- **Template**: Template string with placeholders (for template method)
- **Ignore Empty**: Whether to skip empty inputs

## Usage
1. Connect multiple text outputs to the inputs
2. Choose combination method
3. Configure separator or template as needed
4. The component will output the combined text
            """,
            tags=["logic", "text", "combine", "join", "merge", "concatenate"]
        )
    
    @property
    def inputs(self) -> List[ComponentInput]:
        """Component input definitions."""
        return [
            ComponentInput(
                name="input_1",
                display_name="Text Input 1",
                description="First text input",
                input_type=InputType.TEXT,
                required=False,
                default_value=""
            ),
            ComponentInput(
                name="input_2",
                display_name="Text Input 2",
                description="Second text input",
                input_type=InputType.TEXT,
                required=False,
                default_value=""
            ),
            ComponentInput(
                name="input_3",
                display_name="Text Input 3",
                description="Third text input",
                input_type=InputType.TEXT,
                required=False,
                default_value=""
            ),
            ComponentInput(
                name="input_4",
                display_name="Text Input 4",
                description="Fourth text input",
                input_type=InputType.TEXT,
                required=False,
                default_value=""
            ),
            ComponentInput(
                name="input_5",
                display_name="Text Input 5",
                description="Fifth text input",
                input_type=InputType.TEXT,
                required=False,
                default_value=""
            ),
            ComponentInput(
                name="additional_inputs",
                display_name="Additional Inputs",
                description="Array of additional text inputs",
                input_type=InputType.ARRAY,
                required=False,
                default_value=[]
            ),
            ComponentInput(
                name="separator_override",
                display_name="Separator Override",
                description="Override the default separator",
                input_type=InputType.TEXT,
                required=False
            ),
            ComponentInput(
                name="template_override",
                display_name="Template Override",
                description="Override the default template",
                input_type=InputType.TEXT,
                required=False
            )
        ]
    
    @property
    def outputs(self) -> List[ComponentOutput]:
        """Component output definitions."""
        return [
            ComponentOutput(
                name="combined_text",
                display_name="Combined Text",
                description="The combined text output",
                output_type=OutputType.TEXT
            ),
            ComponentOutput(
                name="input_count",
                display_name="Input Count",
                description="Number of inputs that were combined",
                output_type=OutputType.NUMBER
            ),
            ComponentOutput(
                name="combination_info",
                display_name="Combination Info",
                description="Information about the combination process",
                output_type=OutputType.OBJECT
            )
        ]
    
    async def build_results(self) -> Dict[str, Any]:
        """
        Execute the text combination.
        
        Text Combination Flow:
        1. Collect all text inputs
        2. Filter empty inputs if configured
        3. Apply combination method
        4. Format result
        5. Return combined text with metadata
        """
        self.logger.info("Starting text combination")
        
        # Collect all text inputs
        text_inputs = await self._collect_text_inputs()
        
        # Get override values
        separator_override = self.get_input("separator_override")
        template_override = self.get_input("template_override")
        
        # Determine final configuration
        final_separator = separator_override if separator_override is not None else self.separator
        final_template = template_override if template_override is not None else self.template
        
        # Filter empty inputs if configured
        if self.ignore_empty:
            text_inputs = [text for text in text_inputs if text.strip()]
        
        # Apply combination method
        combined_text = await self._apply_combination_method(
            text_inputs,
            final_separator,
            final_template
        )
        
        # Generate combination info
        combination_info = await self._generate_combination_info(
            text_inputs,
            combined_text
        )
        
        self.logger.info("Text combination completed",
                        input_count=len(text_inputs),
                        output_length=len(combined_text),
                        method=self.combination_method)
        
        return {
            "combined_text": combined_text,
            "input_count": len(text_inputs),
            "combination_info": combination_info
        }
    
    async def _collect_text_inputs(self) -> List[str]:
        """Collect all text inputs from the component."""
        text_inputs = []
        
        # Collect numbered inputs
        for i in range(1, 6):
            input_name = f"input_{i}"
            text_value = self.get_input(input_name, "")
            if text_value:
                text_inputs.append(str(text_value))
        
        # Collect additional inputs array
        additional_inputs = self.get_input("additional_inputs", [])
        for additional_input in additional_inputs:
            if additional_input:
                text_inputs.append(str(additional_input))
        
        return text_inputs
    
    async def _apply_combination_method(
        self,
        text_inputs: List[str],
        separator: str,
        template: Optional[str]
    ) -> str:
        """Apply the specified combination method."""
        if not text_inputs:
            return ""
        
        if self.combination_method == "concatenate":
            return await self._concatenate_texts(text_inputs)
        
        elif self.combination_method == "join":
            return await self._join_texts(text_inputs, separator)
        
        elif self.combination_method == "template":
            return await self._template_combine(text_inputs, template)
        
        elif self.combination_method == "list":
            return await self._list_combine(text_inputs, separator)
        
        else:
            # Default to join
            return await self._join_texts(text_inputs, separator)
    
    async def _concatenate_texts(self, text_inputs: List[str]) -> str:
        """Concatenate texts without any separator."""
        return "".join(text_inputs)
    
    async def _join_texts(self, text_inputs: List[str], separator: str) -> str:
        """Join texts with the specified separator."""
        return separator.join(text_inputs)
    
    async def _template_combine(self, text_inputs: List[str], template: Optional[str]) -> str:
        """Combine texts using a template."""
        if not template:
            # Default template
            template = "{0}"
        
        try:
            # Create variables for template substitution
            template_vars = {}
            
            # Add numbered placeholders
            for i, text in enumerate(text_inputs):
                template_vars[str(i)] = text
                template_vars[f"input_{i+1}"] = text
            
            # Add named placeholders
            template_vars["all"] = self.separator.join(text_inputs)
            template_vars["count"] = len(text_inputs)
            
            # Apply template
            return template.format(**template_vars)
            
        except (KeyError, ValueError, IndexError) as e:
            self.logger.warning("Template combination failed, falling back to join",
                              error=str(e))
            return await self._join_texts(text_inputs, self.separator)
    
    async def _list_combine(self, text_inputs: List[str], separator: str) -> str:
        """Combine texts as a formatted list."""
        if not text_inputs:
            return ""
        
        if len(text_inputs) == 1:
            return text_inputs[0]
        
        # Create numbered list
        list_items = []
        for i, text in enumerate(text_inputs, 1):
            list_items.append(f"{i}. {text}")
        
        return "\n".join(list_items)
    
    async def _generate_combination_info(
        self,
        text_inputs: List[str],
        combined_text: str
    ) -> Dict[str, Any]:
        """Generate information about the combination process."""
        return {
            "method": self.combination_method,
            "input_count": len(text_inputs),
            "input_lengths": [len(text) for text in text_inputs],
            "output_length": len(combined_text),
            "separator_used": self.separator,
            "ignored_empty": self.ignore_empty,
            "preserve_order": self.preserve_order,
            "timestamp": datetime.utcnow().isoformat(),
        }