"""Package configuration module for teradata-mcp-server.

Provides the runtime Settings dataclass, helpers and defaults
Also carries packaged configuration files (e.g., default profiles.yml).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # General
    profile: str | None = None
    database_uri: str | None = None
    config_dir: str | None = None  # User config directory for runtime overrides

    # MCP transport
    mcp_transport: str = "stdio"  # stdio | streamable-http | sse
    mcp_host: str = "localhost"
    mcp_port: int = 8001
    mcp_path: str = "/mcp/"

    # Auth
    auth_mode: str = "none"  # none | basic
    auth_cache_ttl: int = 300

    # Database configuration
    logmech: str = "TD2"
    logmech_is_explicit: bool = False  # True when set via CLI arg or env var
    auth_rate_limit_attempts: int = 5
    auth_rate_limit_window: int = 60
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    # Logging
    logging_level: str = os.getenv("LOGGING_LEVEL", "WARNING")

    # Tools registration and execution method
    progressive_disclosure: bool = False  # Whether to register tools dynamically for MCP access

    # Extension hooks
    hooks_module: str | None = None  # Path to a .py file or dotted module name providing get_hooks()

    # Row limits for query results
    default_row_limit: int = 1000   # Default max rows returned by base_readQuery (DEFAULT_ROW_LIMIT env var)
    max_row_limit: int = 50000      # Hard ceiling; callers cannot exceed this (MAX_ROW_LIMIT env var)


def settings_from_env() -> Settings:
    """Create Settings from environment variables only.
    This avoids mutating os.environ and centralizes precedence.
    """
    return Settings(
        profile=os.getenv("PROFILE") or None,
        database_uri=os.getenv("DATABASE_URI") or None,
        config_dir=os.getenv("CONFIG_DIR") or None,
        mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        mcp_host=os.getenv("MCP_HOST", "localhost"),
        mcp_port=int(os.getenv("MCP_PORT", "8001")),
        mcp_path=os.getenv("MCP_PATH", "/mcp/"),
        auth_mode=os.getenv("AUTH_MODE", "none").lower(),
        auth_cache_ttl=int(os.getenv("AUTH_CACHE_TTL", "300")),
        logmech=os.getenv("LOGMECH", "TD2"),
        logmech_is_explicit=(os.getenv("LOGMECH") is not None),
        auth_rate_limit_attempts=int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5")),
        auth_rate_limit_window=int(os.getenv("AUTH_RATE_LIMIT_WINDOW", "60")),
        pool_size=int(os.getenv("TD_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("TD_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("TD_POOL_TIMEOUT", "30")),
        logging_level=os.getenv("LOGGING_LEVEL", "WARNING"),
        progressive_disclosure=os.getenv("PROGRESSIVE_DISCLOSURE", "false").lower() == "true",
        hooks_module=os.getenv("HOOKS_MODULE") or None,
        default_row_limit=int(os.getenv("DEFAULT_ROW_LIMIT", "1000")),
        max_row_limit=int(os.getenv("MAX_ROW_LIMIT", "50000")),
    )
