"""
Module loader for lazy loading of tool modules based on profile requirements.
"""

import importlib
import inspect
import logging
import re
from typing import Any

logger = logging.getLogger("teradata_mcp_server.module_loader")


class ModuleLoader:
    """
    Handles dynamic loading of tool modules based on profile requirements.
    Only loads modules when their tools are needed by the selected profile.
    """

    # Map tool prefixes to their corresponding module paths
    MODULE_MAP = {
        'bar': 'teradata_mcp_server.tools.bar',
        'base': 'teradata_mcp_server.tools.base',
        'chat': 'teradata_mcp_server.tools.chat',
        'dba': 'teradata_mcp_server.tools.dba',
        'fs': 'teradata_mcp_server.tools.fs',
        'qlty': 'teradata_mcp_server.tools.qlty',
        'rag': 'teradata_mcp_server.tools.rag',
        'sql_opt': 'teradata_mcp_server.tools.sql_opt',
        'sec': 'teradata_mcp_server.tools.sec',
        'tmpl': 'teradata_mcp_server.tools.tmpl',
        'plot': 'teradata_mcp_server.tools.plot',
        'tdvs': 'teradata_mcp_server.tools.tdvs'
    }

    def __init__(self):
        self._loaded_modules: dict[str, Any] = {}
        self._failed_modules: set = set()  # Track modules that failed to load
        self._required_modules: set = set()

    def determine_required_modules(self, config: dict) -> list[str]:
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
        required_modules.add('base')  # Always load base tools for custom queries

        # Check each tool pattern against module prefixes
        for pattern in tool_patterns:
            for prefix, _module_path in self.MODULE_MAP.items():
                # Create a test tool name to see if pattern matches
                test_name = f"{prefix}_test"
                if re.match(pattern, test_name):
                    required_modules.add(prefix)
                    logger.info(f"Pattern '{pattern}' matches module '{prefix}'")

        self._required_modules = required_modules
        return list(required_modules)

    def load_module(self, module_name: str) -> Any | None:
        """
        Load a specific module if it hasn't been loaded yet.

        Args:
            module_name: Name of the module to load

        Returns:
            The loaded module or None if loading fails
        """
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]

        # Don't retry failed modules
        if module_name in self._failed_modules:
            return None

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
            else:
                logger.warning(f"Unknown module: {module_name}")
                return None

        except ImportError as e:
            # Mark module as failed to prevent retry
            self._failed_modules.add(module_name)

            # Provide specific warnings for optional modules
            error_msg = str(e).lower()
            if module_name == 'fs':
                if any(pkg in error_msg for pkg in ['teradataml', 'tdfs4ds']):
                    logger.warning("Feature Store module not available - required packages not installed. Install with: uv sync --extra fs or pip install -e .[fs]")
                else:
                    logger.warning("Feature Store module not available - module missing or packages not installed. Install with: uv sync --extra fs or pip install -e .[fs]")
            else:
                logger.error(f"Failed to load module {module_name}: {e}")
            return None

    def get_all_functions(self) -> dict[str, Any]:
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

    def get_required_yaml_paths(self) -> list:
        """
        Get the paths to YAML files for only the required modules.

        Returns:
            List of file paths/resources for YAML files that should be loaded
        """
        from importlib.resources import files as pkg_files

        yaml_paths = []

        try:
            tools_pkg_root = pkg_files("teradata_mcp_server").joinpath("tools")
            if tools_pkg_root.is_dir():
                for module_name in self._required_modules:
                    if module_name in self.MODULE_MAP:
                        module_dir = tools_pkg_root.joinpath(module_name)
                        if module_dir.is_dir():
                            for entry in module_dir.iterdir():
                                if entry.is_file() and entry.name.endswith('.yml'):
                                    yaml_paths.append(entry)
        except Exception as e:
            import logging
            logger = logging.getLogger("teradata_mcp_server")
            logger.error(f"Failed to load packaged YAML files: {e}")

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
