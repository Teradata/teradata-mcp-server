"""
LLM client for executing test prompts.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import json

try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = AsyncAnthropic = None

try:
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    OpenAI = AsyncOpenAI = None

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from .config import TestConfig
from .result import TestResult, TestPhaseResult, TestStatus

logger = logging.getLogger(__name__)


class TestClient:
    """LLM client for executing tests via MCP."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.client = None
        self.mcp_session = None
        
    async def initialize(self):
        """Initialize the LLM client."""
        if self.config.llm_provider == "anthropic":
            if not Anthropic:
                raise ImportError("anthropic package not installed")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable required")
            self.client = AsyncAnthropic(api_key=api_key)
            
        elif self.config.llm_provider == "openai":
            if not OpenAI:
                raise ImportError("openai package not installed") 
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")
            self.client = AsyncOpenAI(api_key=api_key)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    async def connect_to_mcp_server(self, server_command: List[str]):
        """Connect to the MCP server."""
        try:
            # Start the MCP server process
            self.mcp_session = await stdio_client(server_command).__aenter__()
            logger.info("Connected to MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def disconnect_from_mcp_server(self):
        """Disconnect from the MCP server."""
        if self.mcp_session:
            await self.mcp_session.__aexit__(None, None, None)
            self.mcp_session = None

    async def execute_test(self, test_name: str, test_prompt: str, module_name: str) -> TestResult:
        """Execute a single test prompt and return results."""
        test_result = TestResult(
            test_name=test_name,
            module_name=module_name,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            logger.info(f"Starting test: {test_name}")
            
            # Execute the test prompt with the LLM
            messages = [
                {
                    "role": "user",
                    "content": test_prompt
                }
            ]

            if self.config.llm_provider == "anthropic":
                response = await self._execute_anthropic(messages, test_result)
            else:
                response = await self._execute_openai(messages, test_result)

            # Parse the response to determine success/failure
            success = self._parse_test_result(response, test_result)
            
            test_result.finish(
                status=TestStatus.PASSED if success else TestStatus.FAILED,
                output=response
            )

        except Exception as e:
            logger.error(f"Test {test_name} failed with error: {e}")
            test_result.finish(
                status=TestStatus.ERROR,
                error_message=str(e)
            )

        return test_result

    async def _execute_anthropic(self, messages: List[Dict], test_result: TestResult) -> str:
        """Execute test with Anthropic Claude."""
        response = await self.client.messages.create(
            model=self.config.llm_model,
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature,
            messages=messages
        )
        
        return response.content[0].text if response.content else ""

    async def _execute_openai(self, messages: List[Dict], test_result: TestResult) -> str:
        """Execute test with OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.config.llm_model,
            messages=messages,
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature
        )
        
        return response.choices[0].message.content if response.choices else ""

    def _parse_test_result(self, response: str, test_result: TestResult) -> bool:
        """Parse LLM response to determine test success/failure."""
        # Look for phase indicators and success/failure keywords
        lines = response.lower().split('\n')
        
        current_phase = None
        phase_results = {}
        
        for line in lines:
            line = line.strip()
            
            # Detect phase markers
            if 'phase' in line and any(char.isdigit() for char in line):
                try:
                    phase_num = int(''.join(filter(str.isdigit, line)))
                    phase_name = line.split('phase')[1].strip()
                    current_phase = phase_num
                    phase_results[current_phase] = {
                        'name': phase_name,
                        'status': TestStatus.RUNNING,
                        'output': ''
                    }
                except (ValueError, IndexError):
                    pass
            
            # Look for success/failure indicators
            if current_phase is not None:
                if any(keyword in line for keyword in ['success', 'passed', 'completed successfully']):
                    phase_results[current_phase]['status'] = TestStatus.PASSED
                elif any(keyword in line for keyword in ['failed', 'error', 'fail this test']):
                    phase_results[current_phase]['status'] = TestStatus.FAILED
                
                phase_results[current_phase]['output'] += line + '\n'

        # Create phase results
        for phase_num, phase_data in phase_results.items():
            phase_result = TestPhaseResult(
                phase_name=phase_data['name'],
                phase_number=phase_num,
                status=phase_data['status'],
                start_time=test_result.start_time,
                output=phase_data['output']
            )
            phase_result.finish(phase_data['status'], phase_data['output'])
            test_result.add_phase(phase_result)

        # Overall success if all phases passed or no explicit failures
        failed_phases = sum(1 for phase in phase_results.values() 
                          if phase['status'] == TestStatus.FAILED)
        
        # Also check for general failure indicators in the response
        failure_keywords = ['failed', 'error', 'fail this test', 'unsuccessful']
        has_general_failure = any(keyword in response.lower() for keyword in failure_keywords)
        
        return failed_phases == 0 and not has_general_failure