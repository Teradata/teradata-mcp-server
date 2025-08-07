#!/usr/bin/env python3
"""
Launcher script for the Teradata MCP Testing Framework.
This script redirects to the main test runner in scripts/testing/
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the main test runner."""
    # Path to the main test runner
    main_script = Path(__file__).parent / "scripts" / "testing" / "run_tests.py"
    
    if not main_script.exists():
        print("❌ Main test runner not found at:", main_script)
        return 1
    
    print("🚀 Launching Teradata MCP Testing Framework...")
    print(f"   Using: {main_script}")
    print()
    
    # Execute the main script
    try:
        result = subprocess.run([sys.executable, str(main_script)] + sys.argv[1:], 
                              cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠ Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error launching test runner: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())