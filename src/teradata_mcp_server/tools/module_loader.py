"""
Module loader for lazy loading of tool modules based on profile requirements.
"""

import importlib
import inspect
import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger("teradata_mcp_server.module_loader")


class ModuleLoader:
    """
    Handles dynamic loading of tool modules based on profile requirements.
    Only loads modules when their tools are needed by the selected profile.
    """
    
    # Map tool prefixes to their corresponding module paths
    MODULE_MAP = {
        'base': 'teradata_mcp_server.tools.base',
        'dba': 'teradata_mcp_server.tools.dba', 
        'evs': 'teradata_mcp_server.tools.evs',
        'fs': 'teradata_mcp_server.tools.fs',
        'qlty': 'teradata_mcp_server.tools.qlty',
        'rag': 'teradata_mcp_server.tools.rag',
        'sec': 'teradata_mcp_server.tools.sec',
        'tmpl': 'teradata_mcp_server.tools.tmpl',
    }
    
    def __init__(self):
        self._loaded_modules: Dict[str, Any] = {}
        self._required_modules: set = set()
    
    def determine_required_modules(self, config: dict) -> List[str]:
        """
        Determine which modules are required based on the profile configuration.
        
        Args:
            config: Profile configuration dictionary
            
        Returns:
            List of module names that need to be loaded
        """
        tool_patterns = config.get('tool', [])
        required_modules = set()
        
        # Always load base modules for shared utilities
        required_modules.add('td_connect')
        
        # Check each tool pattern against module prefixes
        for pattern in tool_patterns:
            for prefix, module_path in self.MODULE_MAP.items():
                # Create a test tool name to see if pattern matches
                test_name = f"{prefix}_test"
                if re.match(pattern, test_name):
                    required_modules.add(prefix)
                    logger.info(f"Pattern '{pattern}' matches module '{prefix}'")
        
        # Add EVS connection if EVS tools are needed
        if 'evs' in required_modules:
            required_modules.add('evs_connect')
        
        self._required_modules = required_modules
        return list(required_modules)
    
    def load_module(self, module_name: str) -> Optional[Any]:
        """
        Load a specific module if it hasn't been loaded yet.
        
        Args:
            module_name: Name of the module to load
            
        Returns:
            The loaded module or None if loading fails
        """
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]
        
        try:
            if module_name in self.MODULE_MAP:
                module_path = self.MODULE_MAP[module_name]
                module = importlib.import_module(module_path)
                self._loaded_modules[module_name] = module
                logger.info(f"Loaded module: {module_path}")
                return module
            elif module_name == 'td_connect':
                # Use absolute import to avoid circular dependency
                td_connect = importlib.import_module('teradata_mcp_server.tools.td_connect')
                self._loaded_modules['td_connect'] = td_connect
                logger.info("Loaded td_connect module")
                return td_connect
            elif module_name == 'evs_connect':
                # Use absolute import to avoid circular dependency
                evs_connect = importlib.import_module('teradata_mcp_server.tools.evs_connect')
                self._loaded_modules['evs_connect'] = evs_connect
                logger.info("Loaded evs_connect module")
                return evs_connect
            else:
                logger.warning(f"Unknown module: {module_name}")
                return None
                
        except ImportError as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return None
    
    def get_all_functions(self) -> Dict[str, Any]:
        """
        Get all functions from loaded modules in the same format as the original td import.
        
        Returns:
            Dictionary mapping function names to function objects
        """
        all_functions = {}
        
        # Load required modules
        for module_name in self._required_modules:
            module = self.load_module(module_name)
            if module:
                # Get all functions from the module
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    all_functions[name] = func
                
                # Also get any classes (like TDConn)
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    all_functions[name] = cls
        
        return all_functions
    
    def get_required_yaml_paths(self) -> List[str]:
        """
        Get the paths to YAML files for only the required modules.
        
        Returns:
            List of file paths for YAML files that should be loaded
        """
        import os
        import glob
        
        yaml_paths = []
        base_path = os.path.dirname(__file__)
        
        for module_name in self._required_modules:
            if module_name in self.MODULE_MAP:
                # Get YAML files for this specific module
                module_dir = os.path.join(base_path, module_name)
                if os.path.exists(module_dir):
                    pattern = os.path.join(module_dir, "*.yml")
                    yaml_paths.extend(glob.glob(pattern))
        
        return yaml_paths
    
    def is_module_required(self, module_name: str) -> bool:
        """
        Check if a module is required by the current profile.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is required, False otherwise
        """
        return module_name in self._required_modules