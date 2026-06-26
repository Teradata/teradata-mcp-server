#!/usr/bin/env python3
"""
HTTP transport smoke test.

Starts the server in streamable-http mode on a free port, connects via the MCP
HTTP client, calls list_tools, then shuts down. DATABASE_URI is not required —
tool registration and list_tools work without a live database.

This catches startup-time errors in HTTP-transport-specific code paths (middleware
registration, import errors, constructor errors) that the stdio-based test suite
cannot reach.

Usage:
    python tests/integration/smoke_http.py
    python tests/integration/smoke_http.py --verbose
    python tests/integration/smoke_http.py --ping-interval 10
    python tests/integration/smoke_http.py --server-cmd "docker run ..."
"""

import argparse
import asyncio
import os
import socket
import subprocess
import sys
import time


async def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            await asyncio.sleep(0.5)
    return False


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def run(server_cmd: str, ping_interval: int, verbose: bool) -> bool:
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    host = "127.0.0.1"
    port = _find_free_port()
    url = f"http://{host}:{port}/mcp/"

    env = {
        **os.environ,
        "MCP_TRANSPORT": "streamable-http",
        "MCP_HOST": host,
        "MCP_PORT": str(port),
        "MCP_PING_INTERVAL": str(ping_interval),
        "LOGGING_LEVEL": "INFO" if verbose else "WARNING",
    }

    cmd = server_cmd.split() + [
        "--mcp_transport", "streamable-http",
        "--mcp_host", host,
        "--mcp_port", str(port),
    ]

    print(f"Starting server: {' '.join(cmd)}")
    print(f"  Transport : streamable-http")
    print(f"  Port      : {port}")
    print(f"  Ping      : {ping_interval}s")

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
    )

    try:
        print(f"Waiting for server to bind on port {port}...")
        ready = await _wait_for_port(host, port, timeout=20.0)
        if not ready:
            print("✗ Server did not start within 20 seconds")
            if not verbose:
                _, stderr = proc.communicate(timeout=2)
                if stderr:
                    print(f"  Server stderr:\n{stderr.decode()[:1000]}")
            return False

        print("✓ Server is listening, connecting via MCP HTTP client...")

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ MCP session initialised")

                result = await session.list_tools()
                tool_names = [t.name for t in result.tools]
                print(f"✓ list_tools returned {len(tool_names)} tools")
                if verbose and tool_names:
                    print(f"  Tools: {', '.join(sorted(tool_names)[:10])}" +
                          (" ..." if len(tool_names) > 10 else ""))

        print("\n✓ HTTP transport smoke test PASSED")
        return True

    except Exception as exc:
        print(f"\n✗ HTTP transport smoke test FAILED: {exc}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    parser = argparse.ArgumentParser(description="HTTP transport smoke test for teradata-mcp-server")
    parser.add_argument(
        "--server-cmd",
        default="uv run teradata-mcp-server",
        help="Command used to start the server (default: 'uv run teradata-mcp-server')",
    )
    parser.add_argument(
        "--ping-interval",
        type=int,
        default=30,
        metavar="SECONDS",
        help="MCP_PING_INTERVAL passed to the server (default: 30)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show server output and full tool list")
    args = parser.parse_args()

    passed = asyncio.run(run(args.server_cmd, args.ping_interval, args.verbose))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
