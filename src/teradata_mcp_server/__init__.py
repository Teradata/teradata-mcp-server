"""
teradata_mcp_server
===================

Lightweight MCP server tools for Teradata.
"""

__version__ = "0.1.0"

# Specify what’s available at package level
__all__ = [
    "main",
]

# Expose your main entry function:
from .server import main