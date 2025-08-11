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
import sys
import time
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Dict, List, Optional

# MCP client imports
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class MCPTestRunner:
    def __init__(self, test_cases_file: str = "test_cases.json", verbose: bool = False):
        self.test_cases_file = test_cases_file
        self.test_cases: Dict[str, List[Dict]] = {}
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
        """Load test cases from JSON file."""
        try:
            with open(self.test_cases_file, 'r') as f:
                data = json.load(f)
                self.test_cases = data.get('test_cases', {})
            print(f"✓ Loaded test cases for {len(self.test_cases)} tools")
        except Exception as e:
            print(f"✗ Failed to load test cases: {e}")
            sys.exit(1)

    async def connect_to_server(self, server_command: List[str]):
        """Connect to the MCP server."""
        try:
            print(f"Connecting to MCP server: {' '.join(server_command)}")
            
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
                # Suppress server logging to reduce noise
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "LOGGING_LEVEL": "WARNING"  # Reduce server log verbosity
            }
            
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else [],
                cwd=project_root,
                env=env_vars
            )

            # Connect with proper context management
            if not self.exit_stack:
                self.exit_stack = AsyncExitStack()
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            await asyncio.wait_for(self.session.initialize(), timeout=10.0)
            print("✓ Connected to MCP server")
            
        except Exception as e:
            print(f"✗ Failed to connect to MCP server: {e}")
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
                print(f"  Tools with tests: {', '.join(sorted(testable_tools))}")
                
        except Exception as e:
            print(f"✗ Failed to discover tools: {e}")
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
                    
                    # Determine if test passed
                    if response_status == "success" and (not isinstance(results, dict) or "error" not in results):
                        status = "PASS"
                        error_msg = None
                        
                        # Check for empty results and log warning
                        results_length = len(str(results)) if results else 0
                        has_warning = False
                        if results_length == 0 or (isinstance(results, (list, dict)) and len(results) == 0):
                            print(f"    Warning: Empty results payload")
                            has_warning = True
                    else:
                        status = "FAIL"
                        if isinstance(results, dict) and "error" in results:
                            error_msg = results["error"]
                        else:
                            error_msg = f"Status: {response_status}"
                        results_length = len(str(results)) if results else 0
                    
                    print(f"{status} ({duration:.2f}s)")
                    
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
                    # Fallback for non-JSON responses - capture full response for failures
                    print(f"FAIL (invalid JSON) ({duration:.2f}s)")
                    if self.verbose:
                        print(f"    JSON parse error: {e}")
                        print(f"    Full raw response: {response_text}")
                    
                    return {
                        "tool": tool_name,
                        "test": test_case['name'],
                        "status": "FAIL",
                        "duration": duration,
                        "response_length": len(response_text),
                        "error": f"JSON parse error: {e}",
                        "full_response": response_text,  # Store full response for reporting
                        "response_status": "invalid_json"
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
                
            print(f"\n{tool_name} ({len(test_cases)} tests):")
            
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
                    
                    # For JSON parse errors, show the actual server response as the error
                    if result.get('error', '').startswith('JSON parse error') and 'full_response' in result and result['full_response']:
                        first_line = result['full_response'].split('\n')[0]
                        print(f"    Error: {first_line}")
                    elif result['error']:
                        print(f"    Error: {result['error']}")
                    
                    # Show first line of response for failures (if not already shown as error)
                    if 'full_response' in result and result['full_response']:
                        if not (result.get('error', '').startswith('JSON parse error')):
                            first_line = result['full_response'].split('\n')[0]
                            print(f"    Response: {first_line}")
                    elif self.verbose and 'full_response' in result:
                        response_content = result.get('full_response', 'No response content')
                        first_line = response_content.split('\n')[0]
                        print(f"    Response: {first_line}")
                    
                    # Show additional JSON response details if available
                    if 'response_status' in result:
                        print(f"    Response Status: {result['response_status']}")
                    if 'has_error_in_results' in result and result['has_error_in_results']:
                        print(f"    Has Error in Results: Yes")
                    if result['response_length'] == 0:
                        print(f"    Warning: Empty results payload")
                    
                    print()  # Add blank line between failures for readability

        # Warning details
        warnings = len([r for r in self.results if r.get('has_warning', False)])
        if warnings > 0:
            print(f"\n" + "="*80)
            print("WARNING DETAILS")
            print("="*80)
            for result in self.results:
                if result.get('has_warning', False):
                    print(f"  ⚠ {result['tool']}:{result['test']} - Empty results")
                    print(f"    Test passed but returned no data")
                    print()  # Add blank line between warnings for readability
        
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
        results_file = f"test_results_{timestamp}.json"
        
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
        print("Usage: python run_mcp_tests.py <server_command> [test_cases.json] [--verbose]")
        print("Example: python run_mcp_tests.py 'uv run teradata-mcp-server'")
        sys.exit(1)
    
    server_command = sys.argv[1].split()
    test_cases_file = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "test_cases.json"
    verbose = "--verbose" in sys.argv
    
    runner = MCPTestRunner(test_cases_file, verbose)
    
    try:
        await runner.load_test_cases()
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


if __name__ == "__main__":
    asyncio.run(main())