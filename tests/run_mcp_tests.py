#!/usr/bin/env python3
"""
Parametric MCP Server Test Runner

This script:
1. Connects to the MCP server
2. Discovers available tools
3. Runs test cases only for available tools
4. Reports pass/fail based on response payload
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Dict, List, Optional

# MCP client imports
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class MCPTestRunner:
    def __init__(self, test_cases_files: List[str] = ["tests/cases/core_test_cases.json"], verbose: bool = False):
        self.test_cases_files = test_cases_files if isinstance(test_cases_files, list) else [test_cases_files]
        self.test_cases: Dict[str, List[Dict]] = {}
        self.scripts: Dict[str, Dict] = {"pre_test": [], "post_test": []}
        self.available_tools: List[str] = []
        self.results: List[Dict] = []
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.verbose = verbose

    def _find_project_root(self) -> str:
        """Find the project root directory (contains profiles.yml)."""
        current = os.path.abspath(os.getcwd())
        while current != '/':
            if os.path.exists(os.path.join(current, 'profiles.yml')):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    async def load_test_cases(self):
        """Load test cases from JSON files."""
        try:
            for test_cases_file in self.test_cases_files:
                if os.path.exists(test_cases_file):
                    with open(test_cases_file, 'r') as f:
                        data = json.load(f)
                        file_test_cases = data.get('test_cases', {})
                        file_scripts = data.get('scripts', {})
                        
                        # Merge test cases from this file
                        for tool_name, cases in file_test_cases.items():
                            if tool_name in self.test_cases:
                                self.test_cases[tool_name].extend(cases)
                            else:
                                self.test_cases[tool_name] = cases
                        
                        # Merge scripts from this file
                        for script_type in ['pre_test', 'post_test']:
                            if script_type in file_scripts:
                                if script_type not in self.scripts:
                                    self.scripts[script_type] = []
                                script_info = file_scripts[script_type].copy()
                                script_info['source_file'] = test_cases_file
                                self.scripts[script_type].append(script_info)
                        
                    print(f"✓ Loaded {len(file_test_cases)} tools from {test_cases_file}")
                    if file_scripts:
                        script_count = len([s for s in file_scripts if s in ['pre_test', 'post_test']])
                        print(f"✓ Loaded {script_count} scripts from {test_cases_file}")
                else:
                    print(f"⚠ Test cases file not found: {test_cases_file}")
            
            print(f"✓ Total test cases loaded for {len(self.test_cases)} tools")
        except Exception as e:
            print(f"✗ Failed to load test cases: {e}")
            sys.exit(1)

    async def connect_to_server(self, server_command: List[str]):
        """Connect to the MCP server."""
        try:
            print(f"Starting MCP server: {' '.join(server_command)}")
            
            project_root = self._find_project_root()
            # Require DATABASE_URI from environment
            if not os.environ.get("DATABASE_URI"):
                print("✗ Error: DATABASE_URI environment variable is required")
                print("  Please set DATABASE_URI before running tests:")
                print("  export DATABASE_URI='teradata://user:pass@host:1025/database'")
                sys.exit(1)
            
            env_vars = {
                **os.environ, 
                "MCP_TRANSPORT": "stdio",
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                # Show server logs during startup for debugging
                "LOGGING_LEVEL": "INFO" if self.verbose else "WARNING"
            }
            
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else [],
                cwd=project_root,
                env=env_vars
            )

            print("  Starting server process...")
            # Connect with proper context management
            if not self.exit_stack:
                self.exit_stack = AsyncExitStack()
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            print("  Server process started, establishing MCP session...")
            
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            print("  Initializing MCP protocol...")
            # Try multiple times with increasing timeouts
            max_retries = 3
            timeout_seconds = [5, 10, 15]
            
            for attempt in range(max_retries):
                try:
                    await asyncio.wait_for(self.session.initialize(), timeout=timeout_seconds[attempt])
                    print("✓ Connected to MCP server")
                    return
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        print(f"  Initialization timeout ({timeout_seconds[attempt]}s), retrying... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(1)  # Brief pause before retry
                    else:
                        raise
            
        except asyncio.TimeoutError:
            print("✗ Failed to connect to MCP server: Initialization timeout")
            print("  The server may be taking longer to start. Try:")
            print("  1. Check if the server command is correct")
            print("  2. Verify DATABASE_URI is accessible")
            print("  3. Run with --verbose for more details")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Failed to connect to MCP server: {e}")
            print("  Server startup logs (if any):")
            if self.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    async def discover_tools(self):
        """Discover available tools from the MCP server."""
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
                
            response = await self.session.list_tools()
            self.available_tools = [tool.name for tool in response.tools]
            print(f"✓ Discovered {len(self.available_tools)} available tools")
            
            # Show which test cases we can run
            testable_tools = [tool for tool in self.available_tools if tool in self.test_cases]
            print(f"✓ Found test cases for {len(testable_tools)} tools")

            if testable_tools:
                print(f"\n✓ Tools with tests: {', '.join(sorted(testable_tools))}")

            # Show which test cases we can run
            if len(testable_tools) < len(self.available_tools):
                missing_tools = set(self.available_tools) - set(testable_tools)
                print(f"⚠ Tools without tests: {', '.join(sorted(missing_tools))}")

        except Exception as e:
            print(f"✗ Failed to discover tools: {e}")
            sys.exit(1)

    async def run_scripts(self, script_type: str):
        """Run pre-test or post-test scripts."""
        if script_type not in self.scripts or not self.scripts[script_type]:
            return
        
        scripts_to_run = self.scripts[script_type]
        print(f"\nRunning {script_type.replace('_', '-')} scripts...")
        
        for script in scripts_to_run:
            command = script['command']
            description = script.get('description', 'Running script')
            source_file = script.get('source_file', 'unknown')
            
            print(f"  {description} (from {os.path.basename(source_file)})")
            if self.verbose:
                print(f"    Command: {command}")
            
            try:
                # Run the command and capture output
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env={**os.environ}  # Pass current environment including DATABASE_URI
                )
                
                if result.returncode == 0:
                    print(f"  ✓ Script completed successfully")
                    if self.verbose and result.stdout.strip():
                        print(f"    Output: {result.stdout.strip()}")
                else:
                    print(f"  ✗ Script failed with exit code {result.returncode}")
                    if result.stderr.strip():
                        print(f"    Error: {result.stderr.strip()}")
                    if self.verbose and result.stdout.strip():
                        print(f"    Output: {result.stdout.strip()}")
                    
                    # For pre-test scripts, exit on failure
                    if script_type == 'pre_test':
                        print(f"✗ Pre-test script failure, aborting test run")
                        sys.exit(1)
                        
            except subprocess.TimeoutExpired:
                print(f"  ✗ Script timed out after 5 minutes")
                if script_type == 'pre_test':
                    print(f"✗ Pre-test script timeout, aborting test run")
                    sys.exit(1)
            except Exception as e:
                print(f"  ✗ Script execution failed: {e}")
                if script_type == 'pre_test':
                    print(f"✗ Pre-test script error, aborting test run") 
                    sys.exit(1)

    async def run_test_case(self, tool_name: str, test_case: Dict) -> Dict:
        """Run a single test case."""
        test_name = f"{tool_name}:{test_case['name']}"
        start_time = time.time()
        
        print(f"  Running {test_name}...", end=" ")
        sys.stdout.flush()  # Force flush to ensure clean output
        
        try:
            response = await self.session.call_tool(
                name=tool_name,
                arguments=test_case.get('parameters', {})
            )
            
            duration = time.time() - start_time
            
            # Parse JSON response with status/metadata/results structure
            if hasattr(response, 'content') and response.content:
                try:
                    # Extract text content from MCP response
                    response_text = ""
                    if isinstance(response.content, list):
                        for content_item in response.content:
                            if hasattr(content_item, 'text'):
                                response_text += content_item.text
                    else:
                        response_text = str(response.content)
                    
                    # Parse JSON response
                    response_json = json.loads(response_text)
                    
                    # Check success criteria: status = "success" AND no "error" key in results
                    response_status = response_json.get("status", "").lower()
                    results = response_json.get("results", {})
                    
                    # Initialize variables
                    has_warning = False
                    
                    # Determine if test passed
                    if response_status == "success" and (not isinstance(results, dict) or "error" not in results):
                        status = "PASS"
                        error_msg = None
                        
                        # Check for empty results and log warning
                        results_length = len(str(results)) if results else 0
                        if results_length == 0 or (isinstance(results, (list, dict)) and len(results) == 0):
                            has_warning = True
                    else:
                        status = "FAIL"
                        if isinstance(results, dict) and "error" in results:
                            error_msg = results["error"]
                        else:
                            error_msg = f"Status: {response_status}"
                        results_length = len(str(results)) if results else 0

                    print(f"{"⚠" if has_warning else ""}{status} ({duration:.2f}s)")

                    # Show full response in verbose mode for failures or errors
                    if self.verbose and status == "FAIL":
                        print(f"    Full response: {response_text}")
                    
                    return {
                        "tool": tool_name,
                        "test": test_case['name'],
                        "status": status,
                        "duration": duration,
                        "response_length": results_length,
                        "error": error_msg,
                        "response_status": response_status,
                        "has_error_in_results": isinstance(results, dict) and "error" in results,
                        "full_response": response_text,  # Always store full response
                        "has_warning": has_warning if status == "PASS" else False
                    }
                    
                except json.JSONDecodeError as e:
                    # Fallback for non-JSON responses - these are typically server errors
                    print(f"FAIL (server error) ({duration:.2f}s)")
                    if self.verbose:
                        print(f"    JSON parse error: {e}")
                        print(f"    Server response: {response_text}")
                    
                    # Use first line of error response as the error message
                    error_msg = response_text.strip().split('\n')[0]
                    
                    return {
                        "tool": tool_name,
                        "test": test_case['name'],
                        "status": "FAIL",
                        "duration": duration,
                        "response_length": len(response_text),
                        "error": error_msg,
                        "full_response": response_text,  # Store full response for reporting
                        "response_status": "server_error"
                    }
            else:
                print(f"FAIL (no content) ({duration:.2f}s)")
                return {
                    "tool": tool_name,
                    "test": test_case['name'],
                    "status": "FAIL",
                    "duration": duration,
                    "response_length": 0,
                    "error": "No content in response"
                }
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"FAIL (exception) ({duration:.2f}s)")
            return {
                "tool": tool_name,
                "test": test_case['name'],
                "status": "FAIL", 
                "duration": duration,
                "response_length": 0,
                "error": str(e),
                "full_response": str(e)
            }

    async def run_all_tests(self):
        """Run all test cases for available tools."""
        total_tests = 0
        
        # Count total tests
        for tool_name, test_cases in self.test_cases.items():
            if tool_name in self.available_tools:
                total_tests += len(test_cases)
        
        if total_tests == 0:
            print("✗ No tests to run (no matching tools)")
            return
            
        print(f"\nRunning {total_tests} test cases...")
        print("─" * 60)  # Add separator before tests start
        
        for tool_name, test_cases in self.test_cases.items():
            if tool_name not in self.available_tools:
                continue
            
            for test_case in test_cases:
                result = await self.run_test_case(tool_name, test_case)
                self.results.append(result)
        
        # Add separator after tests complete to separate from any server output
        print("\n" + "─" * 60)
        print("Tests completed")

    def generate_report(self):
        """Generate and print test report."""
        if not self.results:
            print("\nNo test results to report")
            return
            
        # Failed details
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        if failed > 0:
            print(f"\n" + "="*80)
            print("FAILURE DETAILS")
            print("="*80)
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  ✗ {result['tool']}:{result['test']} - FAIL")                    
                    print(f"    Error: {result['error'].split('\n')[0]}")
                    
                    print()  # Add blank line between failures for readability

        # Warning details
        warnings = len([r for r in self.results if r.get('has_warning', False)])
        if warnings > 0:
            print(f"\n" + "="*80)
            print("WARNING DETAILS")
            print("="*80)
            for result in self.results:
                if result.get('has_warning', False):
                    print(f"  ⚠ {result['tool']}:{result['test']} - Empty result set\n")
        
        # Performance summary
        total_time = sum(r['duration'] for r in self.results)
        avg_time = total_time / len(self.results) if self.results else 0
        print(f"\n" + "="*80)
        print("PERFORMANCE")
        print("="*80)
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average Time: {avg_time:.2f}s per test")
        
        # Test report summary at the very end
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        print(f"\n" + "="*80)
        print("TEST REPORT")
        print("="*80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Warnings: {warnings}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Save detailed results
        self.save_results()

    def save_results(self):
        """Save detailed results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure var/test-reports directory exists
        test_reports_dir = "var/test-reports"
        os.makedirs(test_reports_dir, exist_ok=True)
        
        results_file = f"{test_reports_dir}/test_report_{timestamp}.json"
        
        detailed_results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": len([r for r in self.results if r['status'] == 'PASS']),
                "failed": len([r for r in self.results if r['status'] == 'FAIL']),
                "warnings": len([r for r in self.results if r.get('has_warning', False)])
            },
            "results": self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(detailed_results, f, indent=2)
        
        print(f"Detailed results saved to: {results_file}")

    async def cleanup(self):
        """Cleanup resources."""
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception:
                pass
        
        self.session = None
        self.exit_stack = None


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python tests/run_mcp_tests.py <server_command> [test_cases_file1] [test_cases_file2] [...] [--verbose]")
        print("Examples:")
        print("  python tests/run_mcp_tests.py 'uv run teradata-mcp-server'")
        print("  python tests/run_mcp_tests.py 'uv run teradata-mcp-server' tests/cases/core_test_cases.json")
        print("  python tests/run_mcp_tests.py 'uv run teradata-mcp-server' tests/cases/core_test_cases.json tests/cases/fs_test_cases.json")
        print("  python tests/run_mcp_tests.py 'uv run teradata-mcp-server' tests/cases/evs_test_cases.json --verbose")
        sys.exit(1)
    
    server_command = sys.argv[1].split()
    
    # Parse test case files from arguments
    test_cases_files = []
    verbose = "--verbose" in sys.argv
    
    # Check for test case file arguments (anything that doesn't start with --)
    for i in range(2, len(sys.argv)):
        if not sys.argv[i].startswith('--'):
            test_cases_files.append(sys.argv[i])
    
    # Default to core test cases if no files specified
    if not test_cases_files:
        test_cases_files = ["tests/cases/core_test_cases.json"]
    
    runner = MCPTestRunner(test_cases_files, verbose)
    
    try:
        await runner.load_test_cases()
        await runner.run_scripts('pre_test')
        await runner.connect_to_server(server_command)
        await runner.discover_tools()
        await runner.run_all_tests()
        runner.generate_report()
        
        # Give a moment for any remaining server output, then label it
        await asyncio.sleep(0.1)
        print("\n--- MCP Server Log Output ---")
        await asyncio.sleep(0.1)  # Allow any buffered server output to appear
        
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
    finally:
        await runner.cleanup()
        await runner.run_scripts('post_test')


if __name__ == "__main__":
    asyncio.run(main())