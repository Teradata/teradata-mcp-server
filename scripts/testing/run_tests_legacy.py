#!/usr/bin/env python3
"""
Standalone test runner script that bypasses server initialization issues.
"""

import sys
import asyncio
import logging
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import testing components directly
from teradata_mcp_server.testing.config import TestConfig
from teradata_mcp_server.testing.runner import TestRunner
from teradata_mcp_server.testing.result import TestStatus

async def run_all_tests():
    """Run all available tests."""
    print("=" * 80)
    print("TERADATA MCP SERVER - AUTOMATED TEST EXECUTION")
    print("=" * 80)
    
    # Check if we have required environment variables
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("⚠ Warning: No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        print("This demo will simulate test execution without actual LLM calls.")
        simulate = True
    else:
        simulate = False
    
    # Create configuration
    config = TestConfig()
    config.verbose_logging = True
    config.generate_html_report = True
    config.generate_json_report = True
    config.output_directory = "scripts/test_results"
    
    print(f"Configuration:")
    print(f"  Output Directory: {config.output_directory}")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  Timeout: {config.timeout_seconds}s")
    print(f"  Simulation Mode: {simulate}")
    print()
    
    # Initialize runner
    runner = TestRunner(config)
    
    try:
        if simulate:
            # Simulate test discovery and execution
            await simulate_test_run(runner)
        else:
            # Real test execution (requires working MCP server and LLM API)
            await runner.initialize()
            results = await runner.run_all_tests()
            
            # Generate reports
            report_files = runner.reporter.generate_reports(results)
            
            print("\nReports generated:")
            for format_type, file_path in report_files.items():
                if format_type != 'console':
                    print(f"  {format_type.upper()}: {file_path}")
                    
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        if config.verbose_logging:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

async def simulate_test_run(runner):
    """Simulate test discovery and execution for demo purposes."""
    print("🔍 Discovering test prompts...")
    
    # Load test prompts (this should work even without DB connection)
    try:
        runner.load_test_prompts()
        test_count = len(runner.test_prompts)
        print(f"✅ Found {test_count} test prompts")
        
        if test_count > 0:
            print("\nAvailable tests:")
            for test_name, test_data in runner.test_prompts.items():
                print(f"  • {test_name:<25} [{test_data['module']}]")
        else:
            print("⚠ No test prompts found. Make sure you're in the project root directory.")
            
    except Exception as e:
        print(f"❌ Test discovery failed: {e}")
        
        # Try to list what we can find manually
        print("\n🔍 Manually checking for test files...")
        tools_dir = Path("src/teradata_mcp_server/tools")
        if tools_dir.exists():
            objects_files = list(tools_dir.glob("**/*_objects.yml"))
            print(f"Found {len(objects_files)} object definition files:")
            for obj_file in objects_files:
                print(f"  • {obj_file}")
        else:
            print("❌ Tools directory not found at expected location")
    
    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print("To run actual tests:")
    print("1. Set up your LLM API key:")
    print("   export ANTHROPIC_API_KEY='your-key'")
    print("2. Configure your Teradata database:")
    print("   export DATABASE_URI='teradata://user:pass@host:1025/db'")
    print("3. Run: python scripts/run_tests.py")

def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠ Test execution interrupted by user")
        sys.exit(130)

if __name__ == "__main__":
    main()