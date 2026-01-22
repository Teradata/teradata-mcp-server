"""Utilities for Teradata MCP Server.

- Logging setup (structured JSON + console)
- Configuration loading utilities:
  1. Packaged profiles.yml + working directory profiles.yml (working dir wins)
  2. All src/tools/*/*.yml + working directory *.yml (working dir wins)
"""

import json
import logging
import logging.config
import logging.handlers
import os
import sys
from importlib.resources import files as pkg_files
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("teradata_mcp_server")


# -------------------- Logging -------------------- #
class CustomJSONFormatter(logging.Formatter):
    """Custom JSON formatter that can handle extra dicts in log records."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        reserved = {
            'name','msg','args','levelname','levelno','pathname','filename','module','lineno',
            'funcName','created','msecs','relativeCreated','thread','threadName','processName',
            'process','exc_info','exc_text','stack_info','getMessage','message'
        }
        for k, v in record.__dict__.items():
            if k not in reserved:
                if isinstance(v, dict):
                    log_entry.update(v)
                else:
                    log_entry[k] = v
        return json.dumps(log_entry, ensure_ascii=False)


def _default_log_dir(transport: str) -> str | None:
    """Choose a default per-user log directory when not using stdio.
    Returns None for stdio to avoid writing logs when stdout is the protocol stream.
    """
    if (transport or "stdio").lower() == "stdio":
        return None
    if os.name == "nt":  # Windows
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        return os.path.join(base, "TeradataMCP", "Logs")
    if sys.platform == "darwin":  # macOS
        return os.path.join(os.path.expanduser("~/Library/Logs"), "TeradataMCP")
    # Linux/Unix
    base = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    return os.path.join(base, "teradata_mcp_server", "logs")


def setup_logging(level: str = "WARNING", transport: str = "stdio") -> logging.Logger:
    """Configure structured logging.
    - Skips console handler for stdio transport to avoid polluting MCP stdout
    - Picks a sane per-user file log directory when not stdio (override with LOG_DIR)
    - Disable file logging via NO_FILE_LOGS=1
    """
    # Determine handlers to enable
    enable_console = (transport or "stdio").lower() != "stdio"

    # Compute log dir
    log_dir = os.getenv("LOG_DIR")
    if not log_dir:
        log_dir = _default_log_dir(transport) or ""
    if os.getenv("NO_FILE_LOGS", "").lower() in {"1", "true", "yes"}:
        log_dir = ""
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            log_dir = ""  # fall back to no file logging if unwritable

    # Build logging config dynamically
    handlers: dict[str, Any] = {}
    if enable_console:
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        }
    if log_dir:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "filename": os.path.join(log_dir, "teradata_mcp_server.jsonl"),
            "formatter": "json",
            "maxBytes": 1_000_000,
            "backupCount": 3,
        }

    logger_handlers = list(handlers.keys())
    root_handlers = [h for h in handlers if h == "console"]  # only console for root

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
            "json": {"()": CustomJSONFormatter, "datefmt": "%Y-%m-%dT%H:%M:%S%z"},
        },
        "handlers": handlers,
        "loggers": {
            "teradata_mcp_server": {
                "level": "DEBUG",
                "handlers": logger_handlers,
                "propagate": False,
            }
        },
        "root": {"level": level, "handlers": root_handlers},
    }

    logging.config.dictConfig(log_config)
    return logging.getLogger("teradata_mcp_server")


# -------------------- Response formatting -------------------- #
def format_text_response(text: Any):
    """Format a return value into FastMCP content list.
    Strings are pretty-printed if JSON; other values are stringified.
    """
    import json

    from mcp import types

    if isinstance(text, str):
        try:
            parsed = json.loads(text)
            return [types.TextContent(type="text", text=json.dumps(parsed, indent=2, ensure_ascii=False))]
        except json.JSONDecodeError:
            return [types.TextContent(type="text", text=str(text))]
    return [types.TextContent(type="text", text=str(text))]


def format_error_response(error: str):
    return format_text_response(f"Error: {error}")


# -------------------- Type hint resolution -------------------- #
def resolve_type_hint(type_hint):
    """Convert a type hint from string or type to actual type class.

    Args:
        type_hint: Can be a string like 'str', 'int', 'float', 'bool', or an actual type class

    Returns:
        The actual type class (str, int, float, bool, etc.)
    """
    if isinstance(type_hint, type):
        return type_hint

    if isinstance(type_hint, str):
        # Use eval with a restricted namespace for safety
        namespace = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'Any': Any,
        }
        try:
            return eval(type_hint, {"__builtins__": {}}, namespace)
        except (NameError, SyntaxError, TypeError):
            # Fallback to str if evaluation fails
            return str

    return str  # Fallback to str


# -------------------- Configuration loading -------------------- #
def load_profiles(working_dir: Path | None = None) -> dict[str, Any]:
    """
    Load profiles using the layered configuration strategy.

    Uses config_loader to load from:
    1. Packaged src/teradata_mcp_server/config/profiles.yml (developer defaults)
    2. User config directory profiles.yml (runtime overrides)

    Args:
        working_dir: Deprecated parameter for backwards compatibility.
                     Now uses the global config directory set by config_loader.

    Returns:
        Merged profiles dictionary
    """
    from teradata_mcp_server import config_loader

    # Load configuration (uses global config directory set in app.py)
    profiles = config_loader.load_config("profiles.yml")

    logger.info(f"Total profiles loaded: {list(profiles.keys())}")
    return profiles


def load_all_objects(working_dir: Path | None = None) -> dict[str, Any]:
    """
    Load all MCP objects (tools, prompts, etc.) using the layered configuration strategy.

    Loads from:
    1. Packaged src/tools/*/*.yml files (developer defaults)
    2. User config directory *.yml files (runtime overrides)

    Args:
        working_dir: Deprecated parameter for backwards compatibility.
                     Now uses the global config directory set by config_loader.

    Returns:
        Dictionary of all loaded objects
    """
    from teradata_mcp_server import config_loader

    # Use global config directory (set in app.py)
    config_dir = config_loader.get_global_config_dir()

    objects = {}
    allowed_types = {'tool', 'cube', 'prompt', 'glossary'}

    # Load packaged YAML files from src/tools/*/*.yml
    try:
        tools_pkg_root = pkg_files("teradata_mcp_server").joinpath("tools")
        if tools_pkg_root.is_dir():
            for subdir in tools_pkg_root.iterdir():
                if subdir.is_dir():
                    for yml_file in subdir.iterdir():
                        if yml_file.is_file() and yml_file.name.endswith('.yml'):
                            try:
                                loaded = yaml.safe_load(yml_file.read_text(encoding='utf-8')) or {}
                                # Filter by allowed object types
                                filtered = {k: v for k, v in loaded.items()
                                          if isinstance(v, dict) and v.get('type') in allowed_types}
                                objects.update(filtered)
                            except Exception as e:
                                logger.error(f"Failed to load {yml_file}: {e}")
    except Exception as e:
        logger.error(f"Failed to load packaged YAML files: {e}")

    # Load user config directory *.yml files (overrides packaged)
    # Skip special config files like profiles.yml, chat_config.yml, etc.
    skip_files = {'profiles.yml', 'chat_config.yml', 'rag_config.yml', 'sql_opt_config.yml'}

    for yml_file in config_dir.glob("*.yml"):
        if yml_file.name in skip_files:
            continue
        try:
            with open(yml_file, encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
                # Filter by allowed object types
                filtered = {k: v for k, v in loaded.items()
                          if isinstance(v, dict) and v.get('type') in allowed_types}
                if filtered:
                    objects.update(filtered)
                    logger.info(f"Loaded {len(filtered)} objects from user config: {yml_file.name}")
        except Exception as e:
            logger.error(f"Failed to load {yml_file}: {e}")

    logger.info(f"Loaded {len(objects)} total objects")
    return objects


def get_profile_config(profile_name: str | None = None) -> dict[str, Any]:
    """Get profile configuration or return all if no profile specified."""
    if not profile_name:
        return {'tool': ['.*'], 'prompt': ['.*'], 'resource': ['.*']}

    profiles = load_profiles()
    if profile_name not in profiles:
        available = list(profiles.keys())
        raise ValueError(f"Profile '{profile_name}' not found. Available: {available}")

    return profiles[profile_name]


def get_profile_run_config(profile_name: str | None = None) -> dict[str, Any]:
    """Get the 'run' configuration section from a profile."""
    if not profile_name:
        return {}

    profiles = load_profiles()
    if profile_name not in profiles:
        return {}

    profile = profiles[profile_name]
    run_config = profile.get('run', {})

    # Expand environment variables in run config values
    expanded_config = {}
    for key, value in run_config.items():
        if isinstance(value, str):
            import os
            expanded_config[key] = os.path.expandvars(value)
        else:
            expanded_config[key] = value

    return expanded_config


def apply_profile_defaults_to_env(profile_name: str | None = None) -> None:
    """Apply profile run configuration to environment variables if not already set."""
    if not profile_name:
        return

    profile_run_config = get_profile_run_config(profile_name)
    if not profile_run_config:
        return

    import os

    # Map profile run keys to environment variable names
    key_mapping = {
        'database_uri': 'DATABASE_URI',
        'mcp_transport': 'MCP_TRANSPORT',
        'mcp_host': 'MCP_HOST',
        'mcp_port': 'MCP_PORT',
        'mcp_path': 'MCP_PATH',
        'logmech': 'LOGMECH',
    }

    for run_key, run_value in profile_run_config.items():
        env_key = key_mapping.get(run_key, run_key.upper())

        # Only set if environment variable is not already set
        if env_key not in os.environ:
            os.environ[env_key] = str(run_value)
            logger.debug(f"Applied profile default: {env_key}={run_value}")
        else:
            logger.debug(f"Skipped profile default {env_key} (already set to: {os.environ[env_key]})")
