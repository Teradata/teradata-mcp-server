"""
Teradata MCP Server Testing Framework

This package provides automated testing capabilities for the Teradata MCP server,
allowing for regression testing and validation of all tools, prompts, and resources.
"""

from .runner import TestRunner
from .reporter import TestReporter
from .config import TestConfig
from .result import TestResult, TestPhaseResult, TestStatus

__all__ = [
    'TestRunner',
    'TestReporter', 
    'TestConfig',
    'TestResult',
    'TestPhaseResult',
    'TestStatus'
]