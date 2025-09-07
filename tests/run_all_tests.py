#!/usr/bin/env python3
"""
Master Test Runner for FA Calculator

This script runs both core tests and options tests, providing a comprehensive
validation of the FA calculator's functionality.
"""

import subprocess
import sys
from pathlib import Path

def run_test_suite(test_dir: str, test_name: str) -> bool:
    """Run a test suite and return success status"""
    print(f"🧪 Running {test_name}...")
    print("=" * 60)
    
    test_path = Path(__file__).parent / test_dir
    if test_dir == "core-tests":
        runner_script = test_path / "run_core_tests.py"
    elif test_dir == "options-tests":
        runner_script = test_path / "run_options_tests.py"
    else:
        runner_script = test_path / f"run_{test_dir.replace('-', '_')}_tests.py"
    
    if not runner_script.exists():
        print(f"❌ Test runner not found: {runner_script}")
        return False
    
    try:
        result = subprocess.run(
            ["python3", str(runner_script)],
            cwd=test_path,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        if success:
            print(f"✅ {test_name} completed successfully")
        else:
            print(f"❌ {test_name} failed")
        
        print()
        return success
        
    except subprocess.TimeoutExpired:
        print(f"❌ {test_name} timed out")
        print()
        return False
    except Exception as e:
        print(f"❌ {test_name} error: {e}")
        print()
        return False

def main():
    """Run all test suites"""
    print("🚀 FA Calculator - Comprehensive Test Suite")
    print("=" * 60)
    print("Running both core functionality and options tests...")
    print()
    
    # Test suites to run
    test_suites = [
        ("core-tests", "Core Functionality Tests"),
        ("options-tests", "Command-Line Options Tests")
    ]
    
    results = []
    total_passed = 0
    total_failed = 0
    
    # Run each test suite
    for test_dir, test_name in test_suites:
        success = run_test_suite(test_dir, test_name)
        results.append((test_name, success))
        
        if success:
            total_passed += 1
        else:
            total_failed += 1
    
    # Print final summary
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Test Suites Run: {len(test_suites)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print()
    
    # Show individual results
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print()
    
    if total_failed == 0:
        print("🎉 ALL TEST SUITES PASSED!")
        print("The FA Calculator is ready for use.")
    else:
        print(f"⚠️  {total_failed} test suite(s) failed.")
        print("Please review the failures before using the calculator.")
    
    # Return appropriate exit code
    sys.exit(0 if total_failed == 0 else 1)

if __name__ == "__main__":
    main()
