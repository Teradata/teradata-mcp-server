#!/usr/bin/env python3
"""
Simple validation script for the testing framework components only.
This script tests the framework without initializing database connections.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_core_imports():
    """Test that core testing framework components can be imported."""
    print("Testing core imports...")
    
    try:
        # Test individual module imports without triggering server init
        from teradata_mcp_server.testing.result import TestResult, TestPhaseResult, TestStatus
        from teradata_mcp_server.testing.config import TestConfig
        from teradata_mcp_server.testing.reporter import TestReporter
        print("✓ Core testing components imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
        
    return True

def test_result_structures():
    """Test result data structures."""
    print("Testing result structures...")
    
    try:
        from datetime import datetime
        from teradata_mcp_server.testing.result import TestResult, TestPhaseResult, TestStatus
        
        # Create test phase result
        phase = TestPhaseResult(
            phase_name="Test Phase",
            phase_number=1,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        phase.finish(TestStatus.PASSED, "Phase completed successfully")
        assert phase.status == TestStatus.PASSED
        assert phase.duration is not None
        print("✓ Phase result structure works")
        
        # Create test result
        result = TestResult(
            test_name="test_validation",
            module_name="validation",
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        result.add_phase(phase)
        result.finish(TestStatus.PASSED, "Test completed successfully")
        
        assert result.total_phases == 1
        assert result.passed_phases == 1
        assert result.success_rate == 100.0
        print("✓ Test result structure works")
        
    except Exception as e:
        print(f"✗ Result structure test failed: {e}")
        return False
        
    return True

def test_config():
    """Test configuration loading and saving."""
    print("Testing configuration...")
    
    try:
        from teradata_mcp_server.testing.config import TestConfig
        
        # Create default config
        config = TestConfig()
        assert config.timeout_seconds == 300
        assert config.llm_provider == "anthropic"
        print("✓ Default configuration created")
        
        # Test file operations
        test_config_path = "test_validation_config.yml"
        config.save_to_file(test_config_path)
        loaded_config = TestConfig.from_file(test_config_path)
        assert loaded_config.timeout_seconds == config.timeout_seconds
        
        # Clean up
        Path(test_config_path).unlink()
        print("✓ Configuration file operations work")
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False
        
    return True

def test_reporter():
    """Test reporter functionality."""
    print("Testing reporter...")
    
    try:
        from datetime import datetime
        from teradata_mcp_server.testing.config import TestConfig
        from teradata_mcp_server.testing.reporter import TestReporter
        from teradata_mcp_server.testing.result import TestResult, TestPhaseResult, TestStatus
        
        # Create test config and reporter
        config = TestConfig()
        config.output_directory = "test_validation_output"
        reporter = TestReporter(config)
        
        # Create sample test results
        result = TestResult(
            test_name="test_sample",
            module_name="sample",
            status=TestStatus.PASSED,
            start_time=datetime.now()
        )
        result.finish(TestStatus.PASSED, "Test completed")
        
        # Test console report generation
        console_output = reporter.generate_console_report([result])
        assert "TERADATA MCP TEST RESULTS" in console_output
        print("✓ Console report generation works")
        
        # Clean up
        import shutil
        if Path(config.output_directory).exists():
            shutil.rmtree(config.output_directory)
        
    except Exception as e:
        print(f"✗ Reporter test failed: {e}")
        return False
        
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("TERADATA MCP TESTING FRAMEWORK VALIDATION")
    print("=" * 60)
    
    logging.basicConfig(level=logging.WARNING)
    
    tests = [
        test_core_imports,
        test_result_structures,
        test_config,
        test_reporter,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"Test {test.__name__} failed")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ Testing framework validation PASSED")
        print("\nFramework core components are working correctly!")
        return 0
    else:
        print("✗ Testing framework validation FAILED")
        return 1

if __name__ == "__main__":
    exit(main())