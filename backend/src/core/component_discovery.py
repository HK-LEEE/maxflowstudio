"""
Component Discovery Module
Flow: Directory scan → Module loading → Class extraction → Validation
"""

import os
import sys
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import List, Type, Set
import structlog

from .component_base import BaseComponent

logger = structlog.get_logger()


class ComponentDiscovery:
    """
    Handles automatic discovery and loading of component modules.
    
    Discovery Process:
    1. scan_directories() → Walk directory trees for .py files
    2. load_module_from_file() → Dynamic module loading with importlib
    3. extract_component_classes() → Find BaseComponent subclasses
    4. validate_module() → Check module can be loaded safely
    
    Responsibilities:
    - Directory scanning and file discovery
    - Dynamic module loading and cleanup
    - Component class extraction from modules
    - Error tracking during discovery process
    """
    
    def __init__(self):
        """Initialize component discovery system."""
        self.logger = logger.bind(module="component_discovery")
        self._load_errors: List[str] = []
        self._loaded_modules: Set[str] = set()
    
    async def discover_components_in_paths(self, discovery_paths: List[str]) -> List[Type[BaseComponent]]:
        """
        Discover components from multiple directory paths.
        
        Args:
            discovery_paths: List of directory paths to scan
            
        Returns:
            List[Type[BaseComponent]]: Discovered component classes
        """
        all_components = []
        self._load_errors.clear()
        
        for path in discovery_paths:
            try:
                components = await self._scan_directory(path)
                all_components.extend(components)
                self.logger.info("Scanned directory", path=path, components_found=len(components))
            except Exception as e:
                error_msg = f"Failed to scan directory {path}: {str(e)}"
                self._load_errors.append(error_msg)
                self.logger.error("Directory scan failed", path=path, error=str(e))
        
        return all_components
    
    async def _scan_directory(self, directory_path: str) -> List[Type[BaseComponent]]:
        """
        Scan a single directory for component classes.
        
        Args:
            directory_path: Directory to scan
            
        Returns:
            List[Type[BaseComponent]]: Component classes found
        """
        if not os.path.isdir(directory_path):
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        components = []
        directory = Path(directory_path)
        
        for py_file in directory.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private modules
            
            try:
                file_components = await self._load_module_from_file(py_file)
                components.extend(file_components)
            except Exception as e:
                error_msg = f"Failed to load module {py_file}: {str(e)}"
                self._load_errors.append(error_msg)
                self.logger.warning("Module load failed", file=str(py_file), error=str(e))
        
        return components
    
    async def _load_module_from_file(self, file_path: Path) -> List[Type[BaseComponent]]:
        """
        Load a Python module and extract component classes.
        
        Args:
            file_path: Path to Python module file
            
        Returns:
            List[Type[BaseComponent]]: Component classes from module
        """
        module_name = self._generate_module_name(file_path)
        
        # Skip if already loaded
        if module_name in self._loaded_modules:
            return []
        
        # Create module spec and load
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            raise ValueError(f"Cannot create module spec for {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules for relative imports
        sys.modules[module_name] = module
        self._loaded_modules.add(module_name)
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Cleanup on failure
            if module_name in sys.modules:
                del sys.modules[module_name]
            self._loaded_modules.discard(module_name)
            raise e
        
        # Extract component classes
        components = self._extract_component_classes(module, module_name)
        return components
    
    def _extract_component_classes(self, module, module_name: str) -> List[Type[BaseComponent]]:
        """
        Extract component classes from a loaded module.
        
        Args:
            module: Loaded Python module
            module_name: Name of the module
            
        Returns:
            List[Type[BaseComponent]]: Valid component classes
        """
        components = []
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseComponent) and 
                obj != BaseComponent and
                not getattr(obj, '__abstract__', False)):
                
                try:
                    # Basic validation - try to instantiate
                    temp_instance = obj()
                    if self._validate_component_class(temp_instance):
                        components.append(obj)
                        self.logger.debug("Component extracted", 
                                        class_name=obj.__name__,
                                        module=module_name)
                except Exception as e:
                    error_msg = f"Failed to validate component {obj.__name__}: {str(e)}"
                    self._load_errors.append(error_msg)
                    self.logger.warning("Component validation failed", 
                                      class_name=obj.__name__, 
                                      error=str(e))
        
        return components
    
    def _validate_component_class(self, component: BaseComponent) -> bool:
        """
        Basic validation of component class structure.
        
        Args:
            component: Component instance to validate
            
        Returns:
            bool: True if component is valid
        """
        # Check required attributes
        if not hasattr(component, 'metadata') or not component.metadata:
            return False
            
        if not hasattr(component, 'inputs') or not component.inputs:
            return False
            
        if not hasattr(component, 'outputs') or not component.outputs:
            return False
            
        # Check build_results method
        if not hasattr(component, 'build_results') or not callable(component.build_results):
            return False
        
        return True
    
    def _generate_module_name(self, file_path: Path) -> str:
        """
        Generate a unique module name from file path.
        
        Args:
            file_path: Path to module file
            
        Returns:
            str: Unique module name
        """
        try:
            relative_path = file_path.relative_to(file_path.anchor)
        except ValueError:
            # Fallback for complex paths
            relative_path = file_path
        
        module_parts = list(relative_path.parts[:-1])  # Exclude filename
        module_parts.append(file_path.stem)  # Add filename without extension
        
        # Clean up module name
        module_name = ".".join(part.replace("-", "_") for part in module_parts)
        return f"dynamic_components.{module_name}"
    
    def get_load_errors(self) -> List[str]:
        """Get list of errors encountered during discovery."""
        return self._load_errors.copy()
    
    def clear_errors(self) -> None:
        """Clear the error list."""
        self._load_errors.clear()
    
    def cleanup_modules(self) -> None:
        """Clean up loaded modules from sys.modules."""
        for module_name in self._loaded_modules:
            if module_name in sys.modules:
                del sys.modules[module_name]
        self._loaded_modules.clear()