"""
Component Template and Schema Generation Module
Flow: Component class → Metadata extraction → UI schema → Template creation
"""

import inspect
import re
from typing import Dict, List, Any, Type
from collections import defaultdict
import structlog
from pydantic import BaseModel, Field

from .component_base import BaseComponent, ComponentMetadata, ComponentInput, ComponentOutput

logger = structlog.get_logger()


class ComponentTemplate(BaseModel):
    """Component template for frontend consumption."""
    type: str = Field(..., description="Component type identifier")
    metadata: ComponentMetadata = Field(..., description="Component metadata")
    inputs: List[ComponentInput] = Field(..., description="Input definitions")
    outputs: List[ComponentOutput] = Field(..., description="Output definitions")
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="Configuration schema")
    ui_config: Dict[str, Any] = Field(default_factory=dict, description="UI configuration")


class ComponentCategory(BaseModel):
    """Component category grouping."""
    name: str = Field(..., description="Category name")
    display_name: str = Field(..., description="Human-readable category name")
    description: str = Field(default="", description="Category description")
    icon: str = Field(default="folder", description="Category icon")
    components: List[str] = Field(default_factory=list, description="Component types in category")


class ComponentTemplateGenerator:
    """
    Generates component templates and UI configurations.
    
    Template Generation Process:
    1. extract_metadata() → Get component metadata and interface
    2. generate_config_schema() → Create JSON schema for configuration
    3. generate_ui_config() → Create UI rendering configuration
    4. create_template() → Combine into complete template
    
    Responsibilities:
    - Component metadata extraction and validation
    - JSON schema generation for component configuration
    - UI configuration creation for frontend rendering
    - Component type naming and uniqueness management
    """
    
    def __init__(self):
        """Initialize template generator."""
        self.logger = logger.bind(module="component_template")
        self._registered_types: set = set()
    
    async def create_template(self, 
                            component_class: Type[BaseComponent],
                            component_type: str = None) -> ComponentTemplate:
        """
        Create a complete component template.
        
        Args:
            component_class: Component class to create template for
            component_type: Override component type name
            
        Returns:
            ComponentTemplate: Complete component template
        """
        # Create temporary instance for metadata extraction
        try:
            temp_instance = component_class()
            metadata = temp_instance.metadata
            inputs = temp_instance.inputs
            outputs = temp_instance.outputs
        except Exception as e:
            raise ValueError(f"Cannot instantiate component {component_class.__name__}: {str(e)}")
        
        # Validate component interface
        await self._validate_component_interface(temp_instance)
        
        # Generate component type name
        if not component_type:
            component_type = self._generate_component_type(component_class, metadata)
        
        # Generate schemas and configurations
        config_schema = await self._generate_config_schema(component_class)
        ui_config = await self._generate_ui_config(metadata, inputs, outputs)
        
        # Create template
        template = ComponentTemplate(
            type=component_type,
            metadata=metadata,
            inputs=inputs,
            outputs=outputs,
            config_schema=config_schema,
            ui_config=ui_config,
        )
        
        self.logger.info("Template created", 
                        component_type=component_type,
                        class_name=component_class.__name__)
        
        return template
    
    def _generate_component_type(self, 
                               component_class: Type[BaseComponent], 
                               metadata: ComponentMetadata) -> str:
        """
        Generate unique component type identifier.
        
        Args:
            component_class: Component class
            metadata: Component metadata
            
        Returns:
            str: Unique component type name
        """
        # Use metadata name if available, otherwise class name
        base_name = metadata.name or component_class.__name__
        
        # Convert to snake_case
        snake_case = re.sub('([A-Z]+)', r'_\1', base_name).lower().strip('_')
        
        # Ensure uniqueness
        if snake_case in self._registered_types:
            counter = 1
            while f"{snake_case}_{counter}" in self._registered_types:
                counter += 1
            snake_case = f"{snake_case}_{counter}"
        
        self._registered_types.add(snake_case)
        return snake_case
    
    async def _validate_component_interface(self, component: BaseComponent) -> None:
        """
        Validate component interface compliance.
        
        Args:
            component: Component instance to validate
        """
        metadata = component.metadata
        if not metadata.name or not metadata.category:
            raise ValueError("Component must have name and category in metadata")
        
        # Validate input names
        for input_def in component.inputs:
            if not input_def.name.isidentifier():
                raise ValueError(f"Invalid input name: {input_def.name}")
        
        # Validate output names
        for output_def in component.outputs:
            if not output_def.name.isidentifier():
                raise ValueError(f"Invalid output name: {output_def.name}")
        
        # Check build_results method
        if not hasattr(component, 'build_results') or not callable(component.build_results):
            raise ValueError("Component must implement build_results method")
        
        # Validate method signature
        sig = inspect.signature(component.build_results)
        if len(sig.parameters) > 1:  # self is always present
            raise ValueError("build_results method should not take additional parameters")
    
    async def _generate_config_schema(self, component_class: Type[BaseComponent]) -> Dict[str, Any]:
        """
        Generate JSON schema for component configuration.
        
        Args:
            component_class: Component class to analyze
            
        Returns:
            Dict[str, Any]: JSON schema for component configuration
        """
        schema = {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }
        
        # Extract configuration from __init__ parameters
        if hasattr(component_class, '__init__'):
            sig = inspect.signature(component_class.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_schema = self._generate_parameter_schema(param)
                schema["properties"][param_name] = param_schema
        
        return schema
    
    def _generate_parameter_schema(self, param: inspect.Parameter) -> Dict[str, Any]:
        """
        Generate schema for a single parameter.
        
        Args:
            param: Parameter to generate schema for
            
        Returns:
            Dict[str, Any]: Parameter schema
        """
        param_schema = {"type": "string"}  # Default type
        
        # Infer type from annotation
        if param.annotation != param.empty:
            type_mapping = {
                str: "string",
                int: "integer", 
                float: "number",
                bool: "boolean",
                list: "array",
                dict: "object"
            }
            param_schema["type"] = type_mapping.get(param.annotation, "string")
        
        # Add default value
        if param.default != param.empty:
            param_schema["default"] = param.default
        
        return param_schema
    
    async def _generate_ui_config(self,
                                metadata: ComponentMetadata,
                                inputs: List[ComponentInput],
                                outputs: List[ComponentOutput]) -> Dict[str, Any]:
        """
        Generate UI configuration for component display.
        
        Args:
            metadata: Component metadata
            inputs: Component input definitions
            outputs: Component output definitions
            
        Returns:
            Dict[str, Any]: UI configuration
        """
        # Category-based color scheme
        category_colors = {
            "data_sources": "#4CAF50",    # Green
            "processing": "#2196F3",      # Blue
            "ai_ml": "#9C27B0",          # Purple
            "logic": "#FF9800",          # Orange
            "output": "#F44336",         # Red
            "custom": "#607D8B",         # Blue Grey
        }
        
        ui_config = {
            "color": category_colors.get(metadata.category, "#666666"),
            "icon": metadata.icon,
            "category": metadata.category,
            "width": 200,
            "height": max(100, len(inputs) * 25 + len(outputs) * 25 + 50),
            "handles": {
                "inputs": [
                    {
                        "id": inp.name,
                        "label": inp.display_name,
                        "type": inp.input_type.value,
                        "required": inp.required,
                        "position": "left",
                    }
                    for inp in inputs
                ],
                "outputs": [
                    {
                        "id": out.name,
                        "label": out.display_name,
                        "type": out.output_type.value,
                        "position": "right",
                    }
                    for out in outputs
                ],
            },
            "styling": {
                "border_radius": "8px",
                "shadow": "0 2px 4px rgba(0,0,0,0.1)",
                "font_family": "Inter, sans-serif",
                "font_size": "14px",
            },
        }
        
        return ui_config


class ComponentCategoryManager:
    """
    Manages component categories and their mappings.
    
    Responsibilities:
    - Category definition and initialization
    - Component to category mapping
    - Category-based component organization
    """
    
    def __init__(self):
        """Initialize category manager with default categories."""
        self._categories: Dict[str, ComponentCategory] = {}
        self._initialize_default_categories()
    
    def _initialize_default_categories(self) -> None:
        """Initialize default component categories."""
        default_categories = [
            ComponentCategory(
                name="data_sources",
                display_name="Data Sources",
                description="Components for loading and importing data",
                icon="database",
            ),
            ComponentCategory(
                name="processing", 
                display_name="Data Processing",
                description="Components for data transformation and manipulation",
                icon="cog",
            ),
            ComponentCategory(
                name="ai_ml",
                display_name="AI & Machine Learning",
                description="LLM and AI model components",
                icon="brain",
            ),
            ComponentCategory(
                name="logic",
                display_name="Logic & Control",
                description="Flow control and conditional logic components",
                icon="flow",
            ),
            ComponentCategory(
                name="output",
                display_name="Output & Export",
                description="Components for data output and export",
                icon="export",
            ),
            ComponentCategory(
                name="custom",
                display_name="Custom Components",
                description="User-defined custom components",
                icon="puzzle",
            ),
        ]
        
        for category in default_categories:
            self._categories[category.name] = category
    
    def update_category_mappings(self, templates: Dict[str, ComponentTemplate]) -> None:
        """
        Update category component mappings based on templates.
        
        Args:
            templates: Dictionary of component templates
        """
        # Clear existing mappings
        for category in self._categories.values():
            category.components.clear()
        
        # Add components to categories
        for component_type, template in templates.items():
            category_name = template.metadata.category
            if category_name in self._categories:
                self._categories[category_name].components.append(component_type)
            else:
                # Create category if it doesn't exist
                self._categories[category_name] = ComponentCategory(
                    name=category_name,
                    display_name=category_name.replace("_", " ").title(),
                    description=f"Components in {category_name} category",
                    components=[component_type],
                )
    
    def get_categories(self) -> Dict[str, ComponentCategory]:
        """Get all component categories."""
        return self._categories.copy()
    
    def get_category(self, name: str) -> ComponentCategory:
        """Get a specific category by name."""
        return self._categories.get(name)