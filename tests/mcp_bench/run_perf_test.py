#!/usr/bin/env python3
"""Simple MCP Performance Test Runner"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from mcp_streamable_client import MCPStreamableClient


def expand_env_vars(obj):
    """Recursively expand environment variables in strings within a data structure."""
    if isinstance(obj, str):
        # Support both $VAR and ${VAR} syntax
        def replace_env_var(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, match.group(0))  # Return original if not found

        # Pattern matches $VAR or ${VAR}
        pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
        return re.sub(pattern, replace_env_var, obj)
    elif isinstance(obj, dict):
        return {key: expand_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars(item) for item in obj]
    else:
        return obj


def load_config(config_file: str) -> Dict:
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Expand environment variables in the configuration
    return expand_env_vars(config)


async def run_test(config_file: str, verbose: bool = False):
    config = load_config(config_file)

    # Setup logging with verbose flag
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = config['server']
    server_url = f"http://{server['host']}:{server['port']}"

    # Get server-level auth configuration
    server_auth = server.get('auth')

    print(f"\n{'='*60}")
    print(f"MCP PERFORMANCE TEST")
    print(f"Server: {server_url}")
    print(f"Streams: {len(config['streams'])}")
    print(f"{'='*60}\n")

    test_start_time = time.time()

    # Create and run clients
    clients = []
    for stream_config in config['streams']:
        # Use stream-level auth if available, otherwise use server-level auth
        auth_config = stream_config.get('auth', server_auth)

        client = MCPStreamableClient(
            stream_id=stream_config.get('stream_id', 'test'),
            server_url=server_url,
            test_config_path=stream_config['test_config'],
            duration_seconds=stream_config.get('duration', 10),
            loop_tests=stream_config.get('loop', False),
            auth=auth_config
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
    test_end_time = time.time()

    # Collect all metrics
    all_metrics = []
    total_requests = 0
    total_successful = 0
    total_failed = 0
    total_duration = test_end_time - test_start_time

    for client in clients:
        metrics = client.get_metrics()
        all_metrics.append(metrics)
        total_requests += metrics['total_requests']
        total_successful += metrics['successful_requests']
        total_failed += metrics['failed_requests']

    # Display results
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")

    for metrics in all_metrics:
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
        print(f"  Overall Throughput: {total_requests/total_duration:.2f} req/s")
    print(f"{'='*60}\n")

    # Generate detailed report
    generate_report(config, all_metrics, test_start_time, test_end_time, total_duration)


def generate_report(config: Dict, metrics_list: List[Dict], start_time: float, end_time: float, duration: float):
    """Generate detailed performance report."""
    # Create reports directory
    reports_dir = Path("var/mcp-bench/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for report file
    timestamp = datetime.fromtimestamp(start_time).strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"perf_report_{timestamp}.json"

    # Aggregate metrics
    total_requests = sum(m['total_requests'] for m in metrics_list)
    total_successful = sum(m['successful_requests'] for m in metrics_list)
    total_failed = sum(m['failed_requests'] for m in metrics_list)

    # Calculate aggregate response time
    all_response_times = []
    for metrics in metrics_list:
        if metrics['avg_response_time'] > 0:
            all_response_times.append(metrics['avg_response_time'])
    avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0

    # Build detailed report
    report_data = {
        "timestamp": datetime.fromtimestamp(start_time).isoformat(),
        "test_duration": duration,
        "configuration": config,
        "summary": {
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time_ms": avg_response_time * 1000,
            "overall_throughput_rps": total_requests / duration if duration > 0 else 0
        },
        "streams": []
    }

    # Add per-stream details
    for metrics in metrics_list:
        stream_data = {
            "stream_id": metrics['stream_id'],
            "metrics": {
                "total_requests": metrics['total_requests'],
                "successful_requests": metrics['successful_requests'],
                "failed_requests": metrics['failed_requests'],
                "success_rate": metrics['success_rate'],
                "avg_response_time_ms": metrics['avg_response_time'] * 1000,
                "min_response_time_ms": metrics['min_response_time'] * 1000,
                "max_response_time_ms": metrics['max_response_time'] * 1000,
                "throughput_rps": metrics['requests_per_second'],
                "duration": metrics['duration']
            }
        }
        report_data["streams"].append(stream_data)

    # Save report to file
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    print(f"📊 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Performance Test Runner")
    parser.add_argument("config", help="Configuration file path")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show detailed request/response information")
    args = parser.parse_args()

    try:
        asyncio.run(run_test(args.config, args.verbose))
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)