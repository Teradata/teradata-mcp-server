"""
teradata_mcp_server
===================

Lightweight MCP server tools for Teradata.
"""


from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("teradata-mcp-server")
except PackageNotFoundError:
    __version__ = "0.0.0"

import asyncio

from . import server


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())


# Specify what’s available at package level
__all__ = [
    "main",
    "server",
]
