"""Package configuration module for teradata-mcp-server.

Provides the runtime Settings dataclass and helpers, and also carries
packaged configuration files (e.g., default profiles.yml).
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # General
    profile: str | None = None

    # MCP transport
    mcp_transport: str = "stdio"  # stdio | streamable-http | sse
    mcp_host: str = "localhost"
    mcp_port: int = 8001
    mcp_path: str = "/mcp/"

    # Auth
    auth_mode: str = "none"  # none | basic
    auth_cache_ttl: int = 300

    # Logging
    logging_level: str = os.getenv("LOGGING_LEVEL", "WARNING")


def settings_from_env() -> Settings:
    """Create Settings from environment variables only.
    This avoids mutating os.environ and centralizes precedence.
    """
    return Settings(
        profile=os.getenv("PROFILE") or None,
        mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        mcp_host=os.getenv("MCP_HOST", "localhost"),
        mcp_port=int(os.getenv("MCP_PORT", "8001")),
        mcp_path=os.getenv("MCP_PATH", "/mcp/"),
        auth_mode=os.getenv("AUTH_MODE", "none").lower(),
        auth_cache_ttl=int(os.getenv("AUTH_CACHE_TTL", "300")),
        logging_level=os.getenv("LOGGING_LEVEL", "WARNING"),
    )
