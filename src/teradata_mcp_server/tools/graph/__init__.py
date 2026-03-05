"""
Graph dependency analysis tools for Teradata MCP Server.

This module provides tools for analysing object dependencies, lineage tracing,
and impact analysis using Teradata's object dependency metadata.
"""

from .graph_tools import handle_graph_queryDependenciesAgent

__all__ = [
    'handle_graph_queryDependenciesAgent',
]
