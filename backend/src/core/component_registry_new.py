"""
Component Registry - Main Registry System
Flow: Discovery → Template Generation → Registration → Management
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Type, Any
from collections import defaultdict
import structlog
from pydantic import BaseModel, Field

from .component_base import BaseComponent
from .component_discovery import ComponentDiscovery
from .component_template import (
    ComponentTemplate, 
    ComponentTemplateGenerator, 
    ComponentCategoryManager,
    ComponentCategory
)

logger = structlog.get_logger()


class RegistryStats(BaseModel):
    """Component registry statistics."""
    total_components: int = Field(..., description="Total registered components")
    categories: Dict[str, int] = Field(..., description="Components per category")
    discovery_paths: List[str] = Field(..., description="Discovery paths scanned")
    load_errors: List[str] = Field(..., description="Components that failed to load")
    last_scan_time: Optional[str] = Field(default=None, description="Last scan timestamp")


class ComponentRegistry:
    """
    Main component registry for dynamic component management.
    
    Registry Architecture:
    - ComponentDiscovery: Handles module scanning and loading
    - ComponentTemplateGenerator: Creates UI templates and schemas
    - ComponentCategoryManager: Manages component categorization
    
    Core Process:
    1. discover_components() → Use ComponentDiscovery to find component classes
    2. register_component() → Use TemplateGenerator to create templates
    3. manage_categories() → Use CategoryManager to organize components
    4. provide_api() → Expose registry data for frontend consumption
    
    Responsibilities:
    - Coordinate discovery, template generation, and categorization
    - Provide unified API for component access
    - Manage component lifecycle and statistics
    - Handle component instantiation
    """
    
    def __init__(self):
        """Initialize component registry with all subsystems."""
        self._components: Dict[str, Type[BaseComponent]] = {}
        self._templates: Dict[str, ComponentTemplate] = {}
        self._discovery_paths: List[str] = []
        
        # Initialize subsystems
        self._discovery = ComponentDiscovery()
        self._template_generator = ComponentTemplateGenerator()
        self._category_manager = ComponentCategoryManager()
        
        self.logger = logger.bind(registry_id="component_registry")
        self._last_scan_time: Optional[datetime] = None
    
    def add_discovery_path(self, path: str) -> None:
        """
        Add a directory path for component discovery.
        
        Args:
            path: Directory path to scan for components
        """
        if os.path.isdir(path) and path not in self._discovery_paths:
            self._discovery_paths.append(path)
            self.logger.info("Discovery path added", path=path)
    
    async def discover_components(self) -> None:
        """
        Discover and register components from all discovery paths.
        
        Main Discovery Process:
        1. Use ComponentDiscovery to scan paths and load classes
        2. Use TemplateGenerator to create templates for each class
        3. Register components and templates
        4. Update category mappings
        5. Update statistics
        """
        self.logger.info("Starting component discovery", paths=self._discovery_paths)
        
        # Clear previous errors
        discovered_count = 0
        
        # Discover component classes
        component_classes = await self._discovery.discover_components_in_paths(self._discovery_paths)
        
        # Register each discovered component
        for component_class in component_classes:
            try:
                await self._register_component_class(component_class)
                discovered_count += 1
            except Exception as e:
                error_msg = f"Failed to register {component_class.__name__}: {str(e)}"
                self.logger.warning("Component registration failed", 
                                  class_name=component_class.__name__, 
                                  error=str(e))
        
        # Update category mappings
        self._category_manager.update_category_mappings(self._templates)
        
        # Update scan time
        self._last_scan_time = datetime.utcnow()
        
        self.logger.info("Component discovery completed", 
                        total_components=len(self._components),
                        discovered_this_scan=discovered_count,
                        errors=len(self._discovery.get_load_errors()))
    
    async def _register_component_class(self, component_class: Type[BaseComponent]) -> None:
        """
        Register a component class using the template generator.
        
        Args:
            component_class: Component class to register
        """
        # Generate template
        template = await self._template_generator.create_template(component_class)
        
        # Register component and template
        self._components[template.type] = component_class
        self._templates[template.type] = template
        
        self.logger.info("Component registered", 
                        component_type=template.type,
                        class_name=component_class.__name__,
                        category=template.metadata.category)
    
    def register_component(self, component_type: str, component_class: Type[BaseComponent]) -> None:
        """
        Manually register a component class.
        
        Args:
            component_type: Unique component type identifier
            component_class: Component class to register
        """
        if not issubclass(component_class, BaseComponent):
            raise ValueError(f"Component {component_type} must inherit from BaseComponent")
        
        self._components[component_type] = component_class
        self.logger.info("Component manually registered", component_type=component_type)
    
    def get_component_class(self, component_type: str) -> Optional[Type[BaseComponent]]:
        """Get component class by type."""
        return self._components.get(component_type)
    
    def get_component_template(self, component_type: str) -> Optional[ComponentTemplate]:
        """Get component template by type."""
        return self._templates.get(component_type)
    
    def get_all_templates(self) -> Dict[str, ComponentTemplate]:
        """Get all component templates."""
        return self._templates.copy()
    
    def get_templates_by_category(self, category: str) -> List[ComponentTemplate]:
        """Get component templates filtered by category."""
        return [
            template for template in self._templates.values()
            if template.metadata.category == category
        ]
    
    def get_categories(self) -> Dict[str, ComponentCategory]:
        """Get all component categories."""
        return self._category_manager.get_categories()
    
    def get_component_types(self) -> List[str]:
        """Get list of all registered component types."""
        return list(self._components.keys())
    
    def is_registered(self, component_type: str) -> bool:
        """Check if component type is registered."""
        return component_type in self._components
    
    def unregister_component(self, component_type: str) -> bool:
        """
        Unregister a component.
        
        Args:
            component_type: Component type to unregister
            
        Returns:
            bool: True if component was unregistered, False if not found
        """
        if component_type in self._components:
            del self._components[component_type]
            if component_type in self._templates:
                del self._templates[component_type]
            
            # Update category mappings
            self._category_manager.update_category_mappings(self._templates)
            
            self.logger.info("Component unregistered", component_type=component_type)
            return True
        
        return False
    
    def get_registry_stats(self) -> RegistryStats:
        """Get registry statistics."""
        category_counts = defaultdict(int)
        for template in self._templates.values():
            category_counts[template.metadata.category] += 1
        
        # Combine discovery errors
        all_errors = self._discovery.get_load_errors()
        
        return RegistryStats(
            total_components=len(self._components),
            categories=dict(category_counts),
            discovery_paths=self._discovery_paths.copy(),
            load_errors=all_errors,
            last_scan_time=self._last_scan_time.isoformat() if self._last_scan_time else None,
        )
    
    async def create_component_instance(self, component_type: str, **kwargs) -> Optional[BaseComponent]:
        """
        Create a component instance.
        
        Args:
            component_type: Component type to instantiate
            **kwargs: Component configuration parameters
            
        Returns:
            BaseComponent: Component instance or None if type not found
        """
        component_class = self._components.get(component_type)
        if not component_class:
            self.logger.error("Component type not found", component_type=component_type)
            return None
        
        try:
            instance = component_class(**kwargs)
            self.logger.debug("Component instance created", 
                            component_type=component_type,
                            instance_id=instance.id)
            return instance
        except Exception as e:
            self.logger.error("Failed to create component instance", 
                            component_type=component_type,
                            error=str(e))
            return None
    
    def cleanup(self) -> None:
        """Clean up registry resources."""
        self._discovery.cleanup_modules()
        self._components.clear()
        self._templates.clear()
        self.logger.info("Registry cleaned up")


# Create singleton instance
registry = ComponentRegistry()