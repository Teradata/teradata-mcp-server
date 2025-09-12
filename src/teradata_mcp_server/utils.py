"""Utilities for Teradata MCP Server.

- Logging setup (structured JSON + console)
- Configuration loading utilities:
  1. Packaged profiles.yml + working directory profiles.yml (working dir wins)
  2. All src/tools/*/*.yml + working directory *.yml (working dir wins)
"""

import sys
import json
import logging
import logging.config
import logging.handlers
import os
from pathlib import Path
from typing import Dict, Any, Optional
from importlib.resources import files as pkg_files
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


def _default_log_dir(transport: str) -> Optional[str]:
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
    root_handlers = [h for h in handlers.keys() if h == "console"]  # only console for root

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


def load_profiles(working_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load packaged profiles.yml, then working directory profiles.yml (overrides)."""
    if working_dir is None:
        working_dir = Path.cwd()
    
    profiles = {}
    
    # Load packaged profiles.yml
    try:
        import importlib.resources
        try:
            # Try the new importlib.resources API (Python 3.9+)
            config_files = importlib.resources.files("teradata_mcp_server.config")
            profiles_file = config_files / "profiles.yml"
            logger.debug(f"Looking for packaged profiles at: {profiles_file}")
            if profiles_file.is_file():
                packaged_profiles = yaml.safe_load(profiles_file.read_text(encoding='utf-8')) or {}
                profiles.update(packaged_profiles)
                logger.info(f"Loaded {len(packaged_profiles)} packaged profiles: {list(packaged_profiles.keys())}")
            else:
                logger.warning(f"Packaged profiles.yml not found at: {profiles_file}")
        except AttributeError:
            # Fallback for older Python versions
            import importlib.resources as resources
            with resources.path("teradata_mcp_server.config", "profiles.yml") as profiles_path:
                logger.debug(f"Looking for packaged profiles at: {profiles_path}")
                if profiles_path.exists():
                    packaged_profiles = yaml.safe_load(profiles_path.read_text(encoding='utf-8')) or {}
                    profiles.update(packaged_profiles)
                    logger.info(f"Loaded {len(packaged_profiles)} packaged profiles: {list(packaged_profiles.keys())}")
                else:
                    logger.warning(f"Packaged profiles.yml not found at: {profiles_path}")
    except Exception as e:
        logger.error(f"Failed to load packaged profiles: {e}", exc_info=True)
    
    # Load working directory profiles.yml (overrides packaged)
    profiles_path = working_dir / "profiles.yml"
    if profiles_path.exists():
        try:
            with open(profiles_path, encoding='utf-8') as f:
                working_dir_profiles = yaml.safe_load(f) or {}
                profiles.update(working_dir_profiles)
                logger.info(f"Loaded {len(working_dir_profiles)} working directory profiles: {list(working_dir_profiles.keys())}")
        except Exception as e:
            logger.error(f"Failed to load external profiles: {e}")
    else:
        logger.debug(f"No working directory profiles.yml found at: {profiles_path}")
    
    logger.info(f"Total profiles loaded: {list(profiles.keys())}")
    return profiles


def load_all_objects(working_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load all src/tools/*/*.yml, then working directory *.yml (overrides)."""
    if working_dir is None:
        working_dir = Path.cwd()
    
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
    
    # Load working directory *.yml files (overrides packaged)
    for yml_file in working_dir.glob("*.yml"):
        if yml_file.name == "profiles.yml":  # Skip profiles.yml
            continue
        try:
            with open(yml_file, encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
                # Filter by allowed object types
                filtered = {k: v for k, v in loaded.items() 
                          if isinstance(v, dict) and v.get('type') in allowed_types}
                objects.update(filtered)
        except Exception as e:
            logger.error(f"Failed to load {yml_file}: {e}")
    
    logger.info(f"Loaded {len(objects)} total objects")
    return objects


def get_profile_config(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """Get profile configuration or return all if no profile specified."""
    if not profile_name:
        return {'tool': ['.*'], 'prompt': ['.*'], 'resource': ['.*']}
    
    profiles = load_profiles()
    if profile_name not in profiles:
        available = list(profiles.keys())
        raise ValueError(f"Profile '{profile_name}' not found. Available: {available}")
    
    return profiles[profile_name]


def get_profile_run_config(profile_name: Optional[str] = None) -> Dict[str, Any]:
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


def apply_profile_defaults_to_env(profile_name: Optional[str] = None) -> None:
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
