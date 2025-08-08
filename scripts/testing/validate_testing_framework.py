#!/usr/bin/env python3
"""
Validation script for the testing framework.
This script validates that the framework components can be imported and initialized.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all testing framework components can be imported."""
    print("Testing imports...")
    
    try:
        from teradata_mcp_server.testing import (
            TestRunner, TestReporter, TestConfig, TestResult, TestPhaseResult, TestStatus
        )
        print("✓ Main testing components imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    try:
        from teradata_mcp_server.testing.client import TestClient
        from teradata_mcp_server.testing.cli import TestCLI
        print("✓ Client and CLI components imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
        
    return True

def test_config():
    """Test configuration loading and saving."""
    print("Testing configuration...")
    
    try:
        from teradata_mcp_server.testing import TestConfig
        
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

def test_result_structures():
    """Test result data structures."""
    print("Testing result structures...")
    
    try:
        from datetime import datetime
        from teradata_mcp_server.testing import TestResult, TestPhaseResult, TestStatus
        
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

def test_runner_initialization():
    """Test runner can be initialized."""
    print("Testing runner initialization...")
    
    try:
        from teradata_mcp_server.testing import TestRunner, TestConfig
        
        config = TestConfig()
        runner = TestRunner(config)
        
        # Test prompt loading (should work even without actual prompts)
        runner.load_test_prompts()
        print("✓ Test runner initialized successfully")
        
    except Exception as e:
        print(f"✗ Runner initialization failed: {e}")
        return False
        
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("TERADATA MCP TESTING FRAMEWORK VALIDATION")
    print("=" * 60)
    
    logging.basicConfig(level=logging.WARNING)  # Suppress info logs during validation
    
    tests = [
        test_imports,
        test_config,
        test_result_structures,
        test_runner_initialization,
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
        print("\nFramework is ready for use!")
        print("\nNext steps:")
        print("1. Install test dependencies: uv sync --group test")
        print("2. Set up environment variables (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
        print("3. Run tests: teradata-test run --help")
        return 0
    else:
        print("✗ Testing framework validation FAILED")
        print("Please check the error messages above and fix the issues.")
        return 1

if __name__ == "__main__":
    exit(main())