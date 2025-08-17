"""
Test runner for executing automated tests.
"""

import asyncio
import fnmatch
import glob
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .client import TestClient
from .config import TestConfig
from .reporter import TestReporter
from .result import TestResult, TestStatus

logger = logging.getLogger(__name__)


class TestRunner:
    """Main test runner for the testing framework."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.client = TestClient(config)
        self.reporter = TestReporter(config)
        self.test_prompts = {}

    async def initialize(self):
        """Initialize the test runner."""
        await self.client.initialize()
        self.load_test_prompts()
        self.config.ensure_output_dir()

    def load_test_prompts(self):
        """Load all test prompts from module objects files."""
        logger.info("Loading test prompts...")

        tools_dir = Path("src/teradata_mcp_server/tools")
        if not tools_dir.exists():
            raise FileNotFoundError(f"Tools directory not found: {tools_dir}")

        for objects_file in tools_dir.glob("**/*_objects.yml"):
            try:
                with open(objects_file) as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                module_name = objects_file.parent.name

                for prompt_name, prompt_data in data.items():
                    if (prompt_data.get('type') == 'prompt' and
                        any(fnmatch.fnmatch(prompt_name, pattern)
                            for pattern in self.config.test_patterns)):

                        if prompt_name in self.config.excluded_tests:
                            logger.info(f"Skipping excluded test: {prompt_name}")
                            continue

                        if module_name in self.config.excluded_modules:
                            logger.info(f"Skipping test from excluded module: {module_name}")
                            continue

                        self.test_prompts[prompt_name] = {
                            'prompt': prompt_data.get('prompt', ''),
                            'description': prompt_data.get('description', ''),
                            'module': module_name,
                            'file': str(objects_file)
                        }

                        logger.debug(f"Loaded test: {prompt_name} from {module_name}")

            except Exception as e:
                logger.error(f"Error loading {objects_file}: {e}")

        logger.info(f"Loaded {len(self.test_prompts)} test prompts")

    async def run_all_tests(self) -> list[TestResult]:
        """Run all discovered tests."""
        if not self.test_prompts:
            logger.warning("No test prompts found")
            return []

        logger.info(f"Starting test run with {len(self.test_prompts)} tests")
        results = []

        # Connect to MCP server with tester profile
        server_command = [
            "uv", "run", "teradata-mcp-server",
            "--profile", "tester"
        ]

        try:
            await self.client.connect_to_mcp_server(server_command)

            if self.config.parallel_execution:
                results = await self._run_tests_parallel()
            else:
                results = await self._run_tests_sequential()

        finally:
            await self.client.disconnect_from_mcp_server()

        return results

    async def _run_tests_sequential(self) -> list[TestResult]:
        """Run tests sequentially."""
        results = []

        for test_name, test_data in self.test_prompts.items():
            logger.info(f"Running test: {test_name}")

            result = await self.client.execute_test(
                test_name=test_name,
                test_prompt=test_data['prompt'],
                module_name=test_data['module']
            )

            results.append(result)

            # Stop on first failure if configured
            if (self.config.stop_on_first_failure and
                result.status in [TestStatus.FAILED, TestStatus.ERROR]):
                logger.warning(f"Stopping on first failure: {test_name}")
                break

        return results

    async def _run_tests_parallel(self) -> list[TestResult]:
        """Run tests in parallel."""
        tasks = []

        for test_name, test_data in self.test_prompts.items():
            task = self.client.execute_test(
                test_name=test_name,
                test_prompt=test_data['prompt'],
                module_name=test_data['module']
            )
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def run_specific_tests(self, test_names: list[str]) -> list[TestResult]:
        """Run specific named tests."""
        filtered_prompts = {
            name: data for name, data in self.test_prompts.items()
            if name in test_names
        }

        if not filtered_prompts:
            logger.warning(f"No tests found matching: {test_names}")
            return []

        # Temporarily override prompts and run
        original_prompts = self.test_prompts
        self.test_prompts = filtered_prompts

        try:
            results = await self.run_all_tests()
        finally:
            self.test_prompts = original_prompts

        return results

    async def run_module_tests(self, module_names: list[str]) -> list[TestResult]:
        """Run tests for specific modules."""
        filtered_prompts = {
            name: data for name, data in self.test_prompts.items()
            if data['module'] in module_names
        }

        if not filtered_prompts:
            logger.warning(f"No tests found for modules: {module_names}")
            return []

        # Temporarily override prompts and run
        original_prompts = self.test_prompts
        self.test_prompts = filtered_prompts

        try:
            results = await self.run_all_tests()
        finally:
            self.test_prompts = original_prompts

        return results

    def get_available_tests(self) -> list[str]:
        """Get list of available test names."""
        return list(self.test_prompts.keys())

    def get_available_modules(self) -> list[str]:
        """Get list of available module names."""
        return list(set(data['module'] for data in self.test_prompts.values()))
