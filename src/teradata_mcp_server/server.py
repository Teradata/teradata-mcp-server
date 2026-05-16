from __future__ import annotations

import argparse
import asyncio
import os
import signal
from pathlib import Path

from dotenv import load_dotenv

from teradata_mcp_server import __version__, config_loader
from teradata_mcp_server.app import create_mcp_app
from teradata_mcp_server.config import Settings, settings_from_env
from teradata_mcp_server.utils import apply_profile_defaults_to_env


def parse_args_to_settings() -> Settings:
    parser = argparse.ArgumentParser(
        prog="teradata-mcp-server",
        description="Teradata MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--profile", type=str, required=False, help="Profile name to load from profiles.yml")
    parser.add_argument(
        "--config_dir",
        type=str,
        required=False,
        help="Directory for user configuration files (default: current working directory)",
    )
    parser.add_argument("--mcp_transport", type=str, choices=["stdio", "streamable-http", "sse"], required=False)
    parser.add_argument("--mcp_host", type=str, required=False)
    parser.add_argument("--mcp_port", type=int, required=False)
    parser.add_argument("--mcp_path", type=str, required=False)
    parser.add_argument("--database_uri", type=str, required=False, help="Override DATABASE_URI connection string")
    parser.add_argument("--logmech", type=str, required=False)
    parser.add_argument("--auth_mode", type=str, required=False)
    parser.add_argument("--auth_cache_ttl", type=int, required=False)
    parser.add_argument("--logging_level", type=str, required=False)
    parser.add_argument(
        "--progressive_disclosure",
        action="store_true",
        help="Enable progressive disclosure for tool registration instead of static tool listing",
    )
    parser.add_argument(
        "--hooks_module",
        type=str,
        required=False,
        help="Path to a .py file or dotted module name that exports get_hooks() -> ServerHooks",
    )

    args, _ = parser.parse_known_args()

    env = settings_from_env()
    return Settings(
        profile=args.profile if args.profile is not None else env.profile,
        database_uri=args.database_uri if args.database_uri is not None else env.database_uri,
        config_dir=args.config_dir if args.config_dir is not None else env.config_dir,
        mcp_transport=(args.mcp_transport or env.mcp_transport).lower(),
        mcp_host=args.mcp_host if args.mcp_host is not None else env.mcp_host,
        mcp_port=args.mcp_port if args.mcp_port is not None else env.mcp_port,
        mcp_path=args.mcp_path if args.mcp_path is not None else env.mcp_path,
        logmech=args.logmech if args.logmech is not None else env.logmech,
        logmech_is_explicit=(args.logmech is not None) or env.logmech_is_explicit,
        auth_mode=(args.auth_mode or env.auth_mode).lower(),
        auth_cache_ttl=args.auth_cache_ttl if args.auth_cache_ttl is not None else env.auth_cache_ttl,
        logging_level=(args.logging_level or env.logging_level).upper(),
        progressive_disclosure=args.progressive_disclosure or env.progressive_disclosure,
        hooks_module=args.hooks_module if args.hooks_module is not None else env.hooks_module,
        default_row_limit=env.default_row_limit,
        max_row_limit=env.max_row_limit,
    )


async def main():
    load_dotenv()

    # Apply the profile's `run:` defaults to env vars before parsing,
    # so CLI flags and pre-existing env vars still take precedence.
    # We need --config_dir at this point so load_profiles() looks in the
    # right place for user-supplied profiles.yml.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--profile", type=str)
    pre.add_argument("--config_dir", type=str)
    pre_args, _ = pre.parse_known_args()
    config_dir = pre_args.config_dir or os.environ.get("CONFIG_DIR")
    if config_dir:
        config_loader.set_global_config_dir(Path(config_dir).resolve())
    apply_profile_defaults_to_env(pre_args.profile or os.environ.get("PROFILE"))

    settings = parse_args_to_settings()
    mcp, logger = create_mcp_app(settings)

    # Graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        for s in (signal.SIGTERM, signal.SIGINT):
            logger.info(f"Registering signal handler for {s.name}")
            loop.add_signal_handler(s, lambda s=s: os._exit(0))
    except NotImplementedError:
        logger.warning("Signal handling not supported on this platform")

    # Run transport
    if settings.mcp_transport in ["sse", "streamable-http"]:
        await mcp.run_http_async(
            transport=settings.mcp_transport, host=settings.mcp_host, port=settings.mcp_port, path=settings.mcp_path
        )
    else:
        await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
