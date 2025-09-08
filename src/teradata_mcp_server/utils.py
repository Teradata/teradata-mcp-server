"""Utilities for Teradata MCP Server.

Configuration loading utilities:
1. Packaged profiles.yml + working directory profiles.yml (working dir wins)
2. All src/tools/*/*.yml + working directory *.yml (working dir wins)
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from importlib.resources import files as pkg_files
import yaml

logger = logging.getLogger("teradata_mcp_server")


def load_profiles(working_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load packaged profiles.yml, then working directory profiles.yml (overrides)."""
    if working_dir is None:
        working_dir = Path.cwd()
    
    profiles = {}
    
    # Load packaged profiles.yml
    try:
        config_files = pkg_files("teradata_mcp_server.config")
        profiles_file = config_files / "profiles.yml"
        if profiles_file.is_file():
            profiles.update(yaml.safe_load(profiles_file.read_text(encoding='utf-8')) or {})
    except Exception as e:
        logger.error(f"Failed to load packaged profiles: {e}")
    
    # Load working directory profiles.yml (overrides packaged)
    profiles_path = working_dir / "profiles.yml"
    if profiles_path.exists():
        try:
            with open(profiles_path, encoding='utf-8') as f:
                profiles.update(yaml.safe_load(f) or {})
        except Exception as e:
            logger.error(f"Failed to load external profiles: {e}")
    
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