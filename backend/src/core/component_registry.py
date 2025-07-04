"""
Component Registry - Refactored into modular components (627 → 62 lines)
Flow: Import modules → Delegate to specialized classes → Provide unified API
"""

# Re-export from the new modular implementation
from .component_registry_new import ComponentRegistry, RegistryStats
from .component_template import ComponentTemplate, ComponentCategory
from .component_discovery import ComponentDiscovery
from .component_template import ComponentTemplateGenerator, ComponentCategoryManager

# For backward compatibility, create singleton instance
registry = ComponentRegistry()