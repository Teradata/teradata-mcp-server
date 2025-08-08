"""
Command-line interface for the testing framework.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config import TestConfig
from .runner import TestRunner
from .reporter import TestReporter

logger = logging.getLogger(__name__)


class TestCLI:
    """Command-line interface for running tests."""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="Teradata MCP Server Testing Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s run                          # Run all tests
  %(prog)s run --tests test_baseTools   # Run specific test
  %(prog)s run --modules base qlty      # Run tests for specific modules
  %(prog)s run --config custom.yml     # Use custom config file
  %(prog)s list                         # List available tests
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Run command
        run_parser = subparsers.add_parser('run', help='Run tests')
        run_parser.add_argument(
            '--tests', nargs='+', 
            help='Specific test names to run'
        )
        run_parser.add_argument(
            '--modules', nargs='+',
            help='Specific modules to test'
        )
        run_parser.add_argument(
            '--config', '-c',
            help='Configuration file path'
        )
        run_parser.add_argument(
            '--output-dir', '-o',
            help='Output directory for reports'
        )
        run_parser.add_argument(
            '--timeout', type=int,
            help='Test timeout in seconds'
        )
        run_parser.add_argument(
            '--stop-on-failure', action='store_true',
            help='Stop on first test failure'
        )
        run_parser.add_argument(
            '--parallel', action='store_true',
            help='Run tests in parallel'
        )
        run_parser.add_argument(
            '--verbose', '-v', action='store_true',
            help='Verbose output'
        )
        run_parser.add_argument(
            '--json-only', action='store_true',
            help='Generate only JSON report'
        )
        run_parser.add_argument(
            '--html-only', action='store_true',
            help='Generate only HTML report'
        )

        # List command
        list_parser = subparsers.add_parser('list', help='List available tests')
        list_parser.add_argument(
            '--modules', action='store_true',
            help='List available modules instead of tests'
        )

        # Config command
        config_parser = subparsers.add_parser('config', help='Manage configuration')
        config_subparsers = config_parser.add_subparsers(dest='config_action')
        
        config_subparsers.add_parser('create', help='Create default config file')
        config_subparsers.add_parser('show', help='Show current config')

        return parser

    async def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with given arguments."""
        parsed_args = self.parser.parse_args(args)

        if not parsed_args.command:
            self.parser.print_help()
            return 0

        # Set up logging
        log_level = logging.DEBUG if getattr(parsed_args, 'verbose', False) else logging.INFO
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

        try:
            if parsed_args.command == 'run':
                return await self._run_tests(parsed_args)
            elif parsed_args.command == 'list':
                return await self._list_tests(parsed_args)
            elif parsed_args.command == 'config':
                return self._manage_config(parsed_args)
            else:
                self.parser.print_help()
                return 0
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Command failed: {e}")
            if getattr(parsed_args, 'verbose', False):
                logger.exception("Full traceback:")
            return 1

    async def _run_tests(self, args) -> int:
        """Run tests based on arguments."""
        # Load configuration
        config = self._load_config(args)
        
        # Override config with command line arguments
        if args.output_dir:
            config.output_directory = args.output_dir
        if args.timeout:
            config.timeout_seconds = args.timeout
        if args.stop_on_failure:
            config.stop_on_first_failure = True
        if args.parallel:
            config.parallel_execution = True
        if args.verbose:
            config.verbose_logging = True
        if args.json_only:
            config.generate_html_report = False
        if args.html_only:
            config.generate_json_report = False

        # Initialize runner
        runner = TestRunner(config)
        await runner.initialize()

        # Run tests
        if args.tests:
            results = await runner.run_specific_tests(args.tests)
        elif args.modules:
            results = await runner.run_module_tests(args.modules)
        else:
            results = await runner.run_all_tests()

        # Generate reports
        report_files = runner.reporter.generate_reports(results)
        
        if config.generate_json_report and 'json' in report_files:
            logger.info(f"JSON report: {report_files['json']}")
        if config.generate_html_report and 'html' in report_files:
            logger.info(f"HTML report: {report_files['html']}")

        # Return appropriate exit code
        failed_count = sum(1 for r in results if r.status.value in ['failed', 'error'])
        return 1 if failed_count > 0 else 0

    async def _list_tests(self, args) -> int:
        """List available tests or modules."""
        config = TestConfig()
        runner = TestRunner(config)
        runner.load_test_prompts()

        if args.modules:
            modules = runner.get_available_modules()
            print("Available modules:")
            for module in sorted(modules):
                print(f"  {module}")
        else:
            tests = runner.get_available_tests()
            print("Available tests:")
            for test in sorted(tests):
                module = runner.test_prompts[test]['module']
                print(f"  {test:<30} [{module}]")

        return 0

    def _manage_config(self, args) -> int:
        """Manage configuration."""
        if args.config_action == 'create':
            config = TestConfig()
            config_path = 'test_config.yml'
            config.save_to_file(config_path)
            print(f"Default configuration created: {config_path}")
        elif args.config_action == 'show':
            config_path = getattr(args, 'config', 'test_config.yml')
            config = self._load_config(args)
            print(f"Configuration from {config_path}:")
            for key, value in config.__dict__.items():
                print(f"  {key}: {value}")
        
        return 0

    def _load_config(self, args) -> TestConfig:
        """Load configuration from file or create default."""
        config_path = getattr(args, 'config', 'test_config.yml')
        
        if Path(config_path).exists():
            return TestConfig.from_file(config_path)
        else:
            return TestConfig()


def main():
    """Main entry point for the CLI."""
    cli = TestCLI()
    exit_code = asyncio.run(cli.run())
    sys.exit(exit_code)


if __name__ == '__main__':
    main()