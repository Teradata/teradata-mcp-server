#!/usr/bin/env python3
"""
Test individual framework components without server dependencies.
"""

import sys
from pathlib import Path

# Add the testing package directly to path
testing_path = Path(__file__).parent / "src" / "teradata_mcp_server" / "testing"
sys.path.insert(0, str(testing_path))

def test_result_module():
    """Test the result module."""
    print("Testing result module...")
    
    try:
        from result import TestResult, TestPhaseResult, TestStatus
        from datetime import datetime
        
        # Test TestStatus enum
        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.PASSED.value == "passed"
        print("✓ TestStatus enum works")
        
        # Test TestPhaseResult
        phase = TestPhaseResult(
            phase_name="Setup Phase",
            phase_number=1,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        phase.finish(TestStatus.PASSED, "Setup completed successfully")
        assert phase.status == TestStatus.PASSED
        assert phase.duration is not None
        print("✓ TestPhaseResult works")
        
        # Test TestResult
        result = TestResult(
            test_name="test_sample",
            module_name="base",
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        result.add_phase(phase)
        result.finish(TestStatus.PASSED, "Test completed")
        
        assert result.total_phases == 1
        assert result.passed_phases == 1
        assert result.success_rate == 100.0
        print("✓ TestResult works")
        
        return True
        
    except Exception as e:
        print(f"✗ Result module test failed: {e}")
        return False

def test_config_module():
    """Test the config module."""
    print("Testing config module...")
    
    try:
        from config import TestConfig
        import tempfile
        import os
        
        # Test default config
        config = TestConfig()
        assert config.timeout_seconds == 300
        assert config.llm_provider == "anthropic"
        assert config.generate_html_report == True
        print("✓ Default configuration created")
        
        # Test file save/load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save_to_file(temp_path)
            loaded_config = TestConfig.from_file(temp_path)
            assert loaded_config.timeout_seconds == config.timeout_seconds
            assert loaded_config.llm_provider == config.llm_provider
            print("✓ Configuration file operations work")
        finally:
            os.unlink(temp_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Config module test failed: {e}")
        return False

def test_reporter_module():
    """Test the reporter module.""" 
    print("Testing reporter module...")
    
    try:
        from reporter import TestReporter
        from config import TestConfig
        from result import TestResult, TestStatus
        from datetime import datetime
        import tempfile
        import shutil
        
        # Create temp directory for outputs
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create config and reporter
            config = TestConfig()
            config.output_directory = temp_dir
            config.generate_json_report = False  # Skip file generation for test
            config.generate_html_report = False
            reporter = TestReporter(config)
            
            # Create sample test result
            result = TestResult(
                test_name="test_sample",
                module_name="base", 
                status=TestStatus.PASSED,
                start_time=datetime.now()
            )
            result.finish(TestStatus.PASSED, "Test completed successfully")
            
            # Test console report
            console_output = reporter.generate_console_report([result])
            assert "TERADATA MCP TEST RESULTS" in console_output
            assert "test_sample" in console_output
            assert "✓" in console_output  # Pass indicator
            print("✓ Console report generation works")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"✗ Reporter module test failed: {e}")
        return False

def main():
    """Run component tests."""
    print("=" * 60)
    print("TESTING FRAMEWORK COMPONENTS VALIDATION")
    print("=" * 60)
    
    tests = [
        test_result_module,
        test_config_module, 
        test_reporter_module,
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
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ Framework components validation PASSED")
        print("\nCore components are working correctly!")
        return 0
    else:
        print("✗ Framework components validation FAILED")
        return 1

if __name__ == "__main__":
    exit(main())