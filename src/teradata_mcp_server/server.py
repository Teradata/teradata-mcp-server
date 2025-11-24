from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

from teradata_mcp_server.config import Settings, settings_from_env
from teradata_mcp_server.app import create_mcp_app
from teradata_mcp_server import __version__


def parse_args_to_settings() -> Settings:
    parser = argparse.ArgumentParser(
        prog="teradata-mcp-server",
        description="Teradata MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--profile', type=str, required=False)
    parser.add_argument('--mcp_transport', type=str, choices=['stdio', 'streamable-http', 'sse'], required=False)
    parser.add_argument('--mcp_host', type=str, required=False)
    parser.add_argument('--mcp_port', type=int, required=False)
    parser.add_argument('--mcp_path', type=str, required=False)
    parser.add_argument('--database_uri', type=str, required=False, help='Override DATABASE_URI connection string')
    parser.add_argument('--logmech', type=str, required=False)
    parser.add_argument('--auth_mode', type=str, required=False)
    parser.add_argument('--auth_cache_ttl', type=int, required=False)
    parser.add_argument('--logging_level', type=str, required=False)
    # querygrid arguments can be added here as needed
    parser.add_argument('--qg_manager_host', type=str, required=False, help='QueryGrid Manager host')
    parser.add_argument('--qg_manager_port', type=int, required=False, help='QueryGrid Manager port')
    parser.add_argument('--qg_manager_username', type=str, required=False, help='QueryGrid Manager username')
    parser.add_argument('--qg_manager_password', required=False, help='QueryGrid Manager password')
    parser.add_argument('--qg_manager_verify_ssl', type=str, required=False, help='Verify SSL certificates for QueryGrid Manager (true/false, default: true)')



    args, _ = parser.parse_known_args()

    env = settings_from_env()
    return Settings(
        profile=args.profile if args.profile is not None else env.profile,
        database_uri=args.database_uri if args.database_uri is not None else env.database_uri,
        mcp_transport=(args.mcp_transport or env.mcp_transport).lower(),
        mcp_host=args.mcp_host if args.mcp_host is not None else env.mcp_host,
        mcp_port=args.mcp_port if args.mcp_port is not None else env.mcp_port,
        mcp_path=args.mcp_path if args.mcp_path is not None else env.mcp_path,
        logmech=args.logmech if args.logmech is not None else env.logmech,
        auth_mode=(args.auth_mode or env.auth_mode).lower(),
        auth_cache_ttl=args.auth_cache_ttl if args.auth_cache_ttl is not None else env.auth_cache_ttl,
        logging_level=(args.logging_level or env.logging_level).upper(),
        qg_manager_host=args.qg_manager_host if args.qg_manager_host is not None else env.qg_manager_host,
        qg_manager_port=args.qg_manager_port if args.qg_manager_port is not None else env.qg_manager_port,
        qg_manager_username=args.qg_manager_username if args.qg_manager_username is not None else env.qg_manager_username,
        qg_manager_password=args.qg_manager_password if args.qg_manager_password is not None else env.qg_manager_password,
        qg_manager_verify_ssl=args.qg_manager_verify_ssl.lower() in ["true", "1", "yes"] if args.qg_manager_verify_ssl is not None else env.qg_manager_verify_ssl,
    )


async def main():
    load_dotenv()
    settings = parse_args_to_settings()
    mcp, logger, cleanup = create_mcp_app(settings)

    # Graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        for s in (signal.SIGTERM, signal.SIGINT):
            logger.info(f"Registering signal handler for {s.name}")
            loop.add_signal_handler(s, lambda s=s: (cleanup(), os._exit(0)))
    except NotImplementedError:
        logger.warning("Signal handling not supported on this platform")

    # Run transport
    if settings.mcp_transport == 'sse':
        await mcp.run_sse_async(host=settings.mcp_host, port=settings.mcp_port, path=settings.mcp_path)
    elif settings.mcp_transport == 'streamable-http':
        await mcp.run_http_async(transport='streamable-http', host=settings.mcp_host, port=settings.mcp_port, path=settings.mcp_path)
    else:
        await mcp.run_stdio_async()


if __name__ == '__main__':
    asyncio.run(main())
