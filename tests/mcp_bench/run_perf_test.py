#!/usr/bin/env python3
"""Simple MCP Performance Test Runner"""

import asyncio
import json
import logging
import sys
from typing import Dict, List
from mcp_streamable_client import MCPStreamableClient


def load_config(config_file: str) -> Dict:
    with open(config_file, 'r') as f:
        return json.load(f)


async def run_test(config_file: str):
    config = load_config(config_file)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = config['server']
    server_url = f"http://{server['host']}:{server['port']}"

    print(f"\n{'='*60}")
    print(f"MCP PERFORMANCE TEST")
    print(f"Server: {server_url}")
    print(f"Streams: {len(config['streams'])}")
    print(f"{'='*60}\n")

    # Create and run clients
    clients = []
    for stream_config in config['streams']:
        client = MCPStreamableClient(
            stream_id=stream_config.get('stream_id', 'test'),
            server_url=server_url,
            test_config_path=stream_config['test_config'],
            duration_seconds=stream_config.get('duration', 10),
            loop_tests=stream_config.get('loop', False),
            auth=stream_config.get('auth')
        )
        clients.append(client)

    # Run all clients with staggered starts to avoid initialization conflicts
    tasks = []
    for i, client in enumerate(clients):
        # Stagger starts by 0.5 seconds
        async def run_with_delay(c, delay):
            await asyncio.sleep(delay)
            return await c.run()

        tasks.append(run_with_delay(client, i * 0.5))

    await asyncio.gather(*tasks)

    # Display results
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")

    total_requests = 0
    total_successful = 0
    total_failed = 0

    for client in clients:
        metrics = client.get_metrics()
        total_requests += metrics['total_requests']
        total_successful += metrics['successful_requests']
        total_failed += metrics['failed_requests']

        print(f"\nStream {metrics['stream_id']}:")
        print(f"  Requests: {metrics['total_requests']}")
        print(f"  Success Rate: {metrics['success_rate']:.1f}%")
        print(f"  Avg Response: {metrics['avg_response_time']*1000:.2f}ms")
        print(f"  Throughput: {metrics['requests_per_second']:.2f} req/s")

    print(f"\nOVERALL:")
    print(f"  Total Requests: {total_requests}")
    print(f"  Successful: {total_successful}")
    print(f"  Failed: {total_failed}")
    if total_requests > 0:
        print(f"  Success Rate: {(total_successful/total_requests*100):.1f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_perf_test.py <config_file>")
        sys.exit(1)

    try:
        asyncio.run(run_test(sys.argv[1]))
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)