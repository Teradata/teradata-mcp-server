"""Load configuration files with simple override strategy.

Loads static configs from src/teradata_mcp_server/config/*.yml,
then overrides top-level keys with any custom configs from the config directory.
"""

import logging
from importlib.resources import files as pkg_files
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("teradata_mcp_server")

# Global config directory for convenience
_global_config_dir: Path | None = None


def load_yaml(file_path: Path) -> dict[str, Any]:
    """Load YAML file, return empty dict if not found or invalid."""
    try:
        if file_path.exists():
            with open(file_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
    return {}


def load_config(
    config_name: str,
    config_dir: Path | None = None,
    defaults: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Load config: start with defaults, then packaged config, then override with custom config.

    Args:
        config_name: Config filename (e.g., "chat_config.yml")
        config_dir: Directory containing custom configs (default: global config dir or cwd)
        defaults: Default config values (optional)

    Returns:
        Config dictionary with custom values overriding packaged values
    """
    if config_dir is None:
        config_dir = _global_config_dir or Path.cwd()

    # Start with defaults
    config = defaults.copy() if defaults else {}

    # Load packaged config
    try:
        pkg_config = pkg_files("teradata_mcp_server.config") / config_name
        if pkg_config.is_file():
            data = yaml.safe_load(pkg_config.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                config.update(data)
                logger.debug(f"Loaded packaged config: {config_name}")
    except Exception as e:
        logger.error(f"Error loading packaged config {config_name}: {e}")

    # Override with custom config
    custom_path = config_dir / config_name
    custom_config = load_yaml(custom_path)
    if custom_config:
        config.update(custom_config)
        logger.info(f"Overridden keys from {custom_path}: {list(custom_config.keys())}")

    return config


# Backward compatibility alias
load_layered_config = load_config


def set_global_config_dir(config_dir: Path) -> None:
    """Set the global config directory used when config_dir is not specified."""
    global _global_config_dir
    _global_config_dir = config_dir
    logger.info(f"Global config directory set to: {config_dir}")


def get_global_config_dir() -> Path:
    """Get the global config directory, defaults to current working directory."""
    return _global_config_dir or Path.cwd()
