"""Package configuration module for teradata-mcp-server.

Provides the runtime Settings dataclass, helpers and defaults
Also carries packaged configuration files (e.g., default profiles.yml).
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # General
    profile: str | None = None
    database_uri: str | None = None

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
    auth_rate_limit_attempts: int = 5
    auth_rate_limit_window: int = 60
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    # QueryGrid Manager
    qg_manager_host: str | None = None
    qg_manager_port: int | None = None
    qg_manager_username: str | None = None
    qg_manager_password: str | None = None
    qg_manager_verify_ssl: bool = True

    # Logging
    logging_level: str = os.getenv("LOGGING_LEVEL", "WARNING")


def settings_from_env() -> Settings:
    """Create Settings from environment variables only.
    This avoids mutating os.environ and centralizes precedence.
    """
    return Settings(
        profile=os.getenv("PROFILE") or None,
        database_uri=os.getenv("DATABASE_URI") or None,
        mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        mcp_host=os.getenv("MCP_HOST", "localhost"),
        mcp_port=int(os.getenv("MCP_PORT", "8001")),
        mcp_path=os.getenv("MCP_PATH", "/mcp/"),
        auth_mode=os.getenv("AUTH_MODE", "none").lower(),
        auth_cache_ttl=int(os.getenv("AUTH_CACHE_TTL", "300")),
        logmech=os.getenv("LOGMECH", "TD2"),
        auth_rate_limit_attempts=int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5")),
        auth_rate_limit_window=int(os.getenv("AUTH_RATE_LIMIT_WINDOW", "60")),
        pool_size=int(os.getenv("TD_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("TD_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("TD_POOL_TIMEOUT", "30")),
        qg_manager_host=os.getenv("QG_MANAGER_HOST") or None,
        qg_manager_port=int(os.getenv("QG_MANAGER_PORT")) if os.getenv("QG_MANAGER_PORT") else None,
        qg_manager_username=os.getenv("QG_MANAGER_USERNAME") or None,
        qg_manager_password=os.getenv("QG_MANAGER_PASSWORD") or None,
        qg_manager_verify_ssl=os.getenv("QG_MANAGER_VERIFY_SSL", "true").lower() in ["true", "1", "yes"],
        logging_level=os.getenv("LOGGING_LEVEL", "WARNING"),
    )
