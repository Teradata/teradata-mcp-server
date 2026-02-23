# src/tools/__init__.py
"""
Tools package with lazy loading support.
Modules are now loaded on-demand based on profile requirements.
"""

from .module_loader import ModuleLoader
from .td_connect import TDConn as TDConn  # explicit re-export for DB connection

# Create a global module loader instance
_module_loader = None

def initialize_module_loader(config: dict):
    """Initialize the module loader with the given profile configuration."""
    global _module_loader
    _module_loader = ModuleLoader()
    _module_loader.determine_required_modules(config)
    return _module_loader

def get_module_loader():
    """Get the current module loader instance."""
    return _module_loader

def __getattr__(name):
    """
    Dynamic attribute access for lazy loading of functions.
    This is called when an attribute is not found in the module.
    """
    if _module_loader:
        all_functions = _module_loader.get_all_functions()
        if name in all_functions:
            return all_functions[name]
    # If not found, raise AttributeError as usual
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

