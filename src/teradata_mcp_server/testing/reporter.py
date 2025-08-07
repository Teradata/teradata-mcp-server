"""
Test result reporting and output generation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template

from .config import TestConfig
from .result import TestResult, TestStatus

logger = logging.getLogger(__name__)


class TestReporter:
    """Generates test reports in various formats."""

    def __init__(self, config: TestConfig):
        self.config = config

    def generate_reports(self, results: List[TestResult]) -> Dict[str, str]:
        """Generate all configured report formats."""
        generated_files = {}
        
        if self.config.generate_json_report:
            json_file = self.generate_json_report(results)
            generated_files['json'] = json_file

        if self.config.generate_html_report:
            html_file = self.generate_html_report(results)
            generated_files['html'] = html_file

        # Always generate console output
        console_output = self.generate_console_report(results)
        generated_files['console'] = console_output

        return generated_files

    def generate_json_report(self, results: List[TestResult]) -> str:
        """Generate JSON report."""
        output_file = self.config.get_output_dir() / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.__dict__,
            'summary': self._generate_summary(results),
            'results': []
        }

        for result in results:
            result_data = {
                'test_name': result.test_name,
                'module_name': result.module_name,
                'status': result.status.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'duration': result.duration,
                'phases': [],
                'overall_output': result.overall_output,
                'error_message': result.error_message,
                'metadata': result.metadata
            }

            for phase in result.phases:
                phase_data = {
                    'phase_name': phase.phase_name,
                    'phase_number': phase.phase_number,
                    'status': phase.status.value,
                    'start_time': phase.start_time.isoformat(),
                    'end_time': phase.end_time.isoformat() if phase.end_time else None,
                    'duration': phase.duration,
                    'output': phase.output,
                    'error_message': phase.error_message,
                    'tool_calls': phase.tool_calls
                }
                result_data['phases'].append(phase_data)

            report_data['results'].append(result_data)

        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"JSON report generated: {output_file}")
        return str(output_file)

    def generate_html_report(self, results: List[TestResult]) -> str:
        """Generate HTML report."""
        output_file = self.config.get_output_dir() / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teradata MCP Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .test-result { margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }
        .test-header { padding: 15px; background: #f9f9f9; border-bottom: 1px solid #ddd; }
        .test-content { padding: 15px; }
        .phase { margin: 10px 0; padding: 10px; border-left: 3px solid #ddd; }
        .status-passed { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .status-error { color: #fd7e14; font-weight: bold; }
        .status-skipped { color: #6c757d; font-weight: bold; }
        .phase-passed { border-left-color: #28a745; }
        .phase-failed { border-left-color: #dc3545; }
        .phase-error { border-left-color: #fd7e14; }
        .output { background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; white-space: pre-wrap; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f0f0f0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Teradata MCP Test Report</h1>
        <p><strong>Generated:</strong> {{ timestamp }}</p>
        <p><strong>Total Tests:</strong> {{ summary.total_tests }}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr><th>Status</th><th>Count</th><th>Percentage</th></tr>
            <tr><td class="status-passed">Passed</td><td>{{ summary.passed }}</td><td>{{ "%.1f"|format(summary.passed_percentage) }}%</td></tr>
            <tr><td class="status-failed">Failed</td><td>{{ summary.failed }}</td><td>{{ "%.1f"|format(summary.failed_percentage) }}%</td></tr>
            <tr><td class="status-error">Error</td><td>{{ summary.errors }}</td><td>{{ "%.1f"|format(summary.error_percentage) }}%</td></tr>
            <tr><td class="status-skipped">Skipped</td><td>{{ summary.skipped }}</td><td>{{ "%.1f"|format(summary.skipped_percentage) }}%</td></tr>
        </table>
    </div>

    <div class="results">
        <h2>Test Results</h2>
        {% for result in results %}
        <div class="test-result">
            <div class="test-header">
                <h3>{{ result.test_name }} <span class="status-{{ result.status.value }}">{{ result.status.value.upper() }}</span></h3>
                <p><strong>Module:</strong> {{ result.module_name }}</p>
                <p><strong>Duration:</strong> {{ "%.2f"|format(result.duration or 0) }}s</p>
                {% if result.phases %}
                <p><strong>Phases:</strong> {{ result.passed_phases }}/{{ result.total_phases }} passed ({{ "%.1f"|format(result.success_rate) }}%)</p>
                {% endif %}
            </div>
            <div class="test-content">
                {% if result.error_message %}
                <div class="phase phase-error">
                    <h4>Error</h4>
                    <div class="output">{{ result.error_message }}</div>
                </div>
                {% endif %}
                
                {% for phase in result.phases %}
                <div class="phase phase-{{ phase.status.value }}">
                    <h4>Phase {{ phase.phase_number }}: {{ phase.phase_name }} 
                        <span class="status-{{ phase.status.value }}">{{ phase.status.value.upper() }}</span>
                        {% if phase.duration %}({{ "%.2f"|format(phase.duration) }}s){% endif %}
                    </h4>
                    {% if phase.output %}
                    <div class="output">{{ phase.output[:1000] }}{% if phase.output|length > 1000 %}...{% endif %}</div>
                    {% endif %}
                    {% if phase.error_message %}
                    <div class="output">Error: {{ phase.error_message }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
        """

        template = Template(html_template)
        html_content = template.render(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            summary=self._generate_summary(results),
            results=results
        )

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {output_file}")
        return str(output_file)

    def generate_console_report(self, results: List[TestResult]) -> str:
        """Generate console-friendly report."""
        summary = self._generate_summary(results)
        
        lines = [
            "=" * 80,
            "TERADATA MCP TEST RESULTS",
            "=" * 80,
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Tests: {summary['total_tests']}",
            "",
            "SUMMARY:",
            f"  ✓ Passed:  {summary['passed']:2d} ({summary['passed_percentage']:5.1f}%)",
            f"  ✗ Failed:  {summary['failed']:2d} ({summary['failed_percentage']:5.1f}%)",
            f"  ⚠ Errors:  {summary['errors']:2d} ({summary['error_percentage']:5.1f}%)",
            f"  - Skipped: {summary['skipped']:2d} ({summary['skipped_percentage']:5.1f}%)",
            "",
            "DETAILS:",
            "-" * 80
        ]

        for result in results:
            status_icon = {
                TestStatus.PASSED: "✓",
                TestStatus.FAILED: "✗", 
                TestStatus.ERROR: "⚠",
                TestStatus.SKIPPED: "-"
            }.get(result.status, "?")

            duration = f"{result.duration:.2f}s" if result.duration else "N/A"
            
            lines.append(f"{status_icon} {result.test_name:<30} [{result.module_name:<10}] {duration:>8}")
            
            if result.phases:
                lines.append(f"    Phases: {result.passed_phases}/{result.total_phases} passed")
            
            if result.error_message:
                lines.append(f"    Error: {result.error_message}")
            
            lines.append("")

        report = "\n".join(lines)
        print(report)
        return report

    def _generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'passed_percentage': (passed / total * 100) if total > 0 else 0,
            'failed_percentage': (failed / total * 100) if total > 0 else 0,
            'error_percentage': (errors / total * 100) if total > 0 else 0,
            'skipped_percentage': (skipped / total * 100) if total > 0 else 0
        }