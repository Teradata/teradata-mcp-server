"""
Registry module for dynamically loading tools from database objects.

This module enables MCP tools to be defined and registered in the database,
allowing dynamic tool discovery and loading at runtime.
"""

from .registry_loader import RegistryLoader

__all__ = ['RegistryLoader']
