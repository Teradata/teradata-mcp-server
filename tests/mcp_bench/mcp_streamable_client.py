#!/usr/bin/env python3
"""
MCP Client for Performance Testing - MCP SDK Implementation
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


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
    """MCP SDK client for performance testing."""

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
        # Ensure we have the correct URL for MCP SDK with trailing slash
        if not server_url.endswith('/'):
            server_url += '/'
        if not server_url.endswith('mcp/'):
            server_url += 'mcp/'
        self.server_url = server_url
        self.test_config_path = Path(test_config_path)
        self.duration_seconds = duration_seconds
        self.loop_tests = loop_tests
        self.auth = auth or {}
        self.logger = logger or logging.getLogger(f"stream_{stream_id}")

        self.metrics = ClientMetrics(stream_id=stream_id)
        self.test_cases: List[Dict[str, Any]] = []
        self._stop_event = asyncio.Event()

    async def message_handler(self, message):
        """Handle incoming messages from the server (optional for basic usage)."""
        pass

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

    async def list_tools(self, session: ClientSession) -> List[str]:
        """List available tools using MCP SDK."""
        try:
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            self.logger.info(f"Available tools ({len(tool_names)}): {tool_names[:5]}")
            return tool_names
        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}")
            return []

    async def execute_test(self, session: ClientSession, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case using MCP SDK."""
        tool_name = test_case['tool']
        test_name = test_case.get('name', 'unnamed')
        parameters = test_case.get('parameters', {})

        # Verbose logging - show request
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"=== REQUEST: {test_name} ===")
            self.logger.debug(f"Tool: {tool_name}")
            self.logger.debug(f"Arguments: {json.dumps(parameters, indent=2)}")

        start_time = time.time()
        result = {
            'test_name': test_name,
            'tool': tool_name,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'response_time': 0,
            'error': None,
            'response_data': None
        }

        try:
            # Use MCP SDK to call the tool
            response = await session.call_tool(tool_name, arguments=parameters)

            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['response_data'] = response.content

            # Check if response contains an error by examining content
            is_error = False
            error_message = None

            if response.content and len(response.content) > 0:
                first_content = response.content[0]
                if hasattr(first_content, 'text') and first_content.text:
                    # Check if the response text indicates an error
                    text = first_content.text.lower()
                    if ('error' in text and ('validation' in text or 'failed' in text or 'exception' in text)) or \
                       'input validation error' in text or \
                       'traceback' in text or \
                       'failed to connect' in text:
                        is_error = True
                        error_message = first_content.text[:200] + '...' if len(first_content.text) > 200 else first_content.text

            if is_error:
                result['success'] = False
                result['error'] = error_message
                self.metrics.failed_requests += 1

                # Verbose logging - show error response
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"=== RESPONSE: {test_name} ===")
                    self.logger.debug(f"Status: ERROR ({response_time:.3f}s)")
                    self.logger.debug(f"Error content: {error_message}")
                else:
                    self.logger.error(f"✗ {test_name} failed: {error_message}")
            else:
                result['success'] = True
                self.metrics.successful_requests += 1
                self.metrics.request_times.append(response_time)

                # Verbose logging - show successful response
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"=== RESPONSE: {test_name} ===")
                    self.logger.debug(f"Status: SUCCESS ({response_time:.3f}s)")
                    if response.content and len(response.content) > 0:
                        first_content = response.content[0]
                        if hasattr(first_content, 'text'):
                            preview = (first_content.text[:200] + '...') if len(first_content.text) > 200 else first_content.text
                            self.logger.debug(f"Content preview: {preview}")
                        else:
                            self.logger.debug(f"Content type: {type(first_content)}")
                    else:
                        self.logger.debug("Empty content")
                else:
                    self.logger.info(f"✓ {test_name} succeeded in {response_time:.3f}s")

        except Exception as e:
            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['error'] = str(e)
            self.metrics.failed_requests += 1

            # Verbose logging - show error response
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"=== RESPONSE: {test_name} ===")
                self.logger.debug(f"Status: ERROR ({response_time:.3f}s)")
                self.logger.debug(f"Error: {e}")
            else:
                self.logger.error(f"✗ {test_name} failed: {e}")

        finally:
            self.metrics.total_requests += 1

        return result

    async def run_test_loop(self, session: ClientSession):
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
            result = await self.execute_test(session, test_case)
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
        """Main run method using MCP SDK."""
        try:
            # Load test configuration
            await self.load_test_config()

            self.logger.info(f"Connecting to {self.server_url}")

            # Add small random delay to avoid race conditions with multiple clients
            import random
            delay = random.uniform(0, 0.5)
            await asyncio.sleep(delay)

            # Use MCP SDK streamablehttp_client - much simpler!
            async with streamablehttp_client(self.server_url, headers=self.auth) as streams:
                read_stream, write_stream, get_session_id_callback = streams

                async with ClientSession(
                    read_stream,
                    write_stream,
                    message_handler=self.message_handler
                ) as session:
                    # Initialize session with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await session.initialize()
                            self.logger.info(f"Session initialized successfully")
                            break
                        except Exception as e:
                            if attempt < max_retries - 1:
                                self.logger.warning(f"Initialization attempt {attempt + 1} failed: {e}, retrying...")
                                await asyncio.sleep(1)
                            else:
                                raise

                    # List available tools
                    tools = await self.list_tools(session)

                    # Run test loop
                    test_results = await self.run_test_loop(session)

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