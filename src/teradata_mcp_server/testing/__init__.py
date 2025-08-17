"""
Teradata MCP Server Testing Framework

This package provides automated testing capabilities for the Teradata MCP server,
allowing for regression testing and validation of all tools, prompts, and resources.
"""

from .config import TestConfig
from .reporter import TestReporter
from .result import TestPhaseResult, TestResult, TestStatus
from .runner import TestRunner

__all__ = [
    'TestRunner',
    'TestReporter',
    'TestConfig',
    'TestResult',
    'TestPhaseResult',
    'TestStatus'
]
