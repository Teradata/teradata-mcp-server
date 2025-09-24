#!/usr/bin/env python3
"""
MCP Client for Performance Testing - Direct HTTP Implementation
"""

import asyncio
import json
import logging
import time
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ClientMetrics:
    """Metrics collected for each client stream."""
    stream_id: str
    start_time: float = 0
    end_time: float = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    request_times: List[float] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def avg_response_time(self) -> float:
        return sum(self.request_times) / len(self.request_times) if self.request_times else 0

    @property
    def min_response_time(self) -> float:
        return min(self.request_times) if self.request_times else 0

    @property
    def max_response_time(self) -> float:
        return max(self.request_times) if self.request_times else 0

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time

    @property
    def requests_per_second(self) -> float:
        return self.total_requests / self.duration if self.duration > 0 else 0


class MCPStreamableClient:
    """Direct HTTP MCP client for performance testing."""

    def __init__(
        self,
        stream_id: str,
        server_url: str,
        test_config_path: str,
        duration_seconds: int,
        loop_tests: bool = False,
        auth: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.stream_id = stream_id

        # Ensure we have the correct URL format
        if not server_url.endswith('/'):
            server_url += '/'
        if not server_url.endswith('mcp/'):
            server_url += 'mcp/'

        self.server_url = server_url
        self.test_config_path = Path(test_config_path)
        self.duration_seconds = duration_seconds
        self.loop_tests = loop_tests
        self.auth = auth
        self.logger = logger or logging.getLogger(f"stream_{stream_id}")

        self.metrics = ClientMetrics(stream_id=stream_id)
        self.test_cases: List[Dict[str, Any]] = []
        self._stop_event = asyncio.Event()
        self.session_id: Optional[str] = None
        self.request_id = 1

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        if self.auth:
            headers.update(self.auth)
        return headers

    def _parse_sse_response(self, response_text: str) -> Optional[Dict]:
        """Parse SSE response to extract JSON data."""
        for line in response_text.split('\n'):
            if line.startswith('data: '):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
        return None

    async def load_test_config(self):
        """Load test cases from configuration file."""
        try:
            with open(self.test_config_path, 'r') as f:
                config = json.load(f)

            # Extract test cases
            if 'test_cases' in config:
                for tool_name, cases in config['test_cases'].items():
                    for case in cases:
                        self.test_cases.append({
                            'tool': tool_name,
                            'name': case.get('name', f"{tool_name}_test"),
                            'parameters': case.get('parameters', {})
                        })
            elif 'tests' in config:
                self.test_cases = config['tests']

            self.logger.info(f"Loaded {len(self.test_cases)} test cases")
        except Exception as e:
            self.logger.error(f"Failed to load test config: {e}")
            raise

    async def initialize_session(self, client: httpx.AsyncClient) -> bool:
        """Initialize MCP session."""
        # Step 1: Send initialize request
        data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": f"perf-test-{self.stream_id}", "version": "1.0.0"}
            },
            "id": self.request_id
        }
        self.request_id += 1

        headers = self._get_headers()
        response = await client.post(self.server_url, headers=headers, json=data)

        if response.status_code == 200:
            self.session_id = response.headers.get('mcp-session-id')
            result = self._parse_sse_response(response.text)

            if result and 'result' in result:
                server_info = result['result'].get('serverInfo', {})
                self.logger.info(f"Session initialized: {self.session_id}")
                self.logger.info(f"Server: {server_info.get('name')} v{server_info.get('version')}")

                # Step 2: Send initialized notification
                notification_data = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                headers = self._get_headers()
                notification_response = await client.post(self.server_url, headers=headers, json=notification_data)

                if notification_response.status_code in [200, 202]:
                    self.logger.info("Initialized notification sent successfully")
                    return True
                else:
                    self.logger.warning(f"Initialized notification returned {notification_response.status_code}")
                    return True  # Still continue even if notification fails

        self.logger.error(f"Failed to initialize: {response.status_code}")
        return False

    async def list_tools(self, client: httpx.AsyncClient) -> List[str]:
        """List available tools."""
        data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self.request_id
        }
        self.request_id += 1

        response = await client.post(self.server_url, headers=self._get_headers(), json=data)
        if response.status_code == 200:
            result = self._parse_sse_response(response.text)
            if result and 'result' in result:
                return [t['name'] for t in result['result'].get('tools', [])]
        return []

    async def execute_test(self, client: httpx.AsyncClient, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case."""
        tool_name = test_case['tool']
        test_name = test_case.get('name', 'unnamed')
        parameters = test_case.get('parameters', {})

        # Check if this is a protocol method (contains /)
        if '/' in tool_name:
            # Direct protocol method call
            data = {
                "jsonrpc": "2.0",
                "method": tool_name,
                "params": parameters,
                "id": self.request_id
            }
        else:
            # Tool call
            data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                },
                "id": self.request_id
            }
        self.request_id += 1

        start_time = time.time()
        result = {
            'test_name': test_name,
            'tool': tool_name,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'response_time': 0,
            'error': None
        }

        try:
            response = await client.post(
                self.server_url,
                headers=self._get_headers(),
                json=data,
                timeout=30.0
            )

            response_time = time.time() - start_time
            result['response_time'] = response_time

            if response.status_code == 200:
                response_data = self._parse_sse_response(response.text)
                if response_data:
                    if 'result' in response_data:
                        result['success'] = True
                        self.metrics.successful_requests += 1
                        self.metrics.request_times.append(response_time)
                        self.logger.debug(f"Test {test_name} succeeded in {response_time:.3f}s")
                    elif 'error' in response_data:
                        result['error'] = response_data['error'].get('message', 'Unknown error')
                        self.metrics.failed_requests += 1
                        self.logger.error(f"Test {test_name} failed: {result['error']}")
            else:
                result['error'] = f"HTTP {response.status_code}"
                self.metrics.failed_requests += 1

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['error'] = "Request timeout"
            self.metrics.failed_requests += 1
            self.logger.error(f"Test {test_name} timed out")

        except Exception as e:
            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['error'] = str(e)
            self.metrics.failed_requests += 1
            self.logger.error(f"Test {test_name} failed: {e}")

        finally:
            self.metrics.total_requests += 1

        return result

    async def run_test_loop(self, client: httpx.AsyncClient):
        """Run test cases in a loop until duration expires."""
        self.metrics.start_time = time.time()
        end_time = self.metrics.start_time + self.duration_seconds
        test_index = 0
        test_results = []

        self.logger.info(f"Starting test loop for {self.duration_seconds} seconds")

        while time.time() < end_time and not self._stop_event.is_set():
            if test_index >= len(self.test_cases):
                if self.loop_tests:
                    test_index = 0
                else:
                    self.logger.info("All tests completed, stopping stream")
                    break

            test_case = self.test_cases[test_index]
            result = await self.execute_test(client, test_case)
            test_results.append(result)

            test_index += 1

            # Small delay to prevent overwhelming the server
            await asyncio.sleep(0.01)

        self.metrics.end_time = time.time()
        self.logger.info(f"Test loop completed. Duration: {self.metrics.duration:.2f}s, "
                        f"Tests executed: {len(test_results)}, "
                        f"Successful: {self.metrics.successful_requests}, "
                        f"Failed: {self.metrics.failed_requests}")

        return test_results

    async def run(self):
        """Main run method for the client stream."""
        try:
            # Load test configuration
            await self.load_test_config()

            self.logger.info(f"Connecting to {self.server_url}")

            async with httpx.AsyncClient() as client:
                # Initialize session
                if not await self.initialize_session(client):
                    raise RuntimeError("Failed to initialize MCP session")

                # List available tools
                tools = await self.list_tools(client)
                self.logger.info(f"Available tools ({len(tools)}): {tools[:5]}")

                # Run test loop
                test_results = await self.run_test_loop(client)

                self.logger.info(f"Stream {self.stream_id} completed successfully")
                return test_results

        except Exception as e:
            self.logger.error(f"Stream {self.stream_id} failed: {e}")
            raise

        finally:
            self.logger.info(f"Stream {self.stream_id} finished")

    def stop(self):
        """Signal the client to stop."""
        self._stop_event.set()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as dictionary."""
        return {
            'stream_id': self.metrics.stream_id,
            'duration': self.metrics.duration,
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_rate': self.metrics.success_rate,
            'avg_response_time': self.metrics.avg_response_time,
            'min_response_time': self.metrics.min_response_time,
            'max_response_time': self.metrics.max_response_time,
            'requests_per_second': self.metrics.requests_per_second,
            'errors': self.metrics.errors
        }