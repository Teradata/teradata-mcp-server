#!/usr/bin/env python3
"""
Aggressive MCP client that mimics Claude Desktop behavior
"""

import asyncio
import json
import logging
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def aggressive_test():
    """Test with rapid-fire requests like Claude Desktop might send"""

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("aggressive_test")

    server_url = "http://localhost:8002/mcp/"  # Use proxy

    async with streamablehttp_client(server_url) as streams:
        read_stream, write_stream, get_session_id_callback = streams

        async with ClientSession(read_stream, write_stream) as session:
            logger.info("Starting aggressive test...")

            # Send multiple requests simultaneously during initialization
            tasks = []

            # This simulates what Claude Desktop might do
            tasks.append(asyncio.create_task(session.initialize()))

            # Send tools/list immediately without waiting for initialization
            await asyncio.sleep(0.001)  # Tiny delay to start init first
            tasks.append(asyncio.create_task(session.list_tools()))

            # Send more requests rapidly
            await asyncio.sleep(0.001)
            tasks.append(asyncio.create_task(session.list_prompts()))
            tasks.append(asyncio.create_task(session.list_resources()))

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {i} failed: {result}")
                    else:
                        logger.info(f"Task {i} succeeded")
            except Exception as e:
                logger.error(f"Gather failed: {e}")

if __name__ == "__main__":
    asyncio.run(aggressive_test())