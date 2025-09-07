#!/usr/bin/env python3
"""
Core Tests Runner for FA Calculator
Tests the core calculation logic using pre-cached data (no internet required)
"""

import os
import sys
import subprocess
import csv
from pathlib import Path
from typing import List, Dict, Tuple

# Color codes for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class CoreTestRunner:
    def __init__(self):
        self.script_dir = Path(__file__).parent.parent.parent.absolute()
        self.fa_calculator = self.script_dir / "fa_calculator.py"
        self.core_tests_dir = Path(__file__).parent
        self.passed = 0
        self.failed = 0
        self.test_results = []
        
    def find_test_directories(self) -> List[Path]:
        """Find all data directories in core-tests"""
        test_dirs = []
        if self.core_tests_dir.exists():
            for item in self.core_tests_dir.iterdir():
                if item.is_dir() and item.name.startswith('data'):
                    test_dirs.append(item)
        return sorted(test_dirs)
    
    def get_test_year_from_config(self, test_dir: Path) -> int:
        """Get the test year from test_config.txt or default to 2023"""
        config_file = test_dir / "test_config.txt"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith("year="):
                            return int(line.split("=")[1].strip())
            except:
                pass
        return 2023  # Default test year
    
    def run_fa_calculator(self, test_dir: Path, year: int) -> Tuple[bool, str]:
        """Run fa_calculator.py for a test directory"""
        try:
            cmd = [
                sys.executable, str(self.fa_calculator),
                "--data", str(test_dir),
                str(year),
                "--no-internet",
                "-x",  # Skip validation for faster tests
                "-y"   # Skip sorting
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "Success"
            else:
                return False, f"Exit code {result.returncode}: {result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return False, "Test timed out"
        except Exception as e:
            return False, f"Error running test: {str(e)}"
    
    def compare_csv_files(self, generated_file: Path, expected_file: Path) -> Tuple[bool, str]:
        """Compare generated FA.csv with expected FA.csv"""
        try:
            if not generated_file.exists():
                return False, "Generated FA.csv not found"
            
            if not expected_file.exists():
                return False, "Expected FA.csv not found"
            
            # Read both files
            with open(generated_file, 'r') as f:
                generated_lines = f.readlines()
            
            with open(expected_file, 'r') as f:
                expected_lines = f.readlines()
            
            # Compare line by line
            if len(generated_lines) != len(expected_lines):
                return False, f"Line count mismatch: generated={len(generated_lines)}, expected={len(expected_lines)}"
            
            for i, (gen_line, exp_line) in enumerate(zip(generated_lines, expected_lines)):
                gen_line = gen_line.strip()
                exp_line = exp_line.strip()
                
                if i == 0:  # Header line - exact match
                    if gen_line != exp_line:
                        return False, f"Header mismatch at line {i+1}"
                else:  # Data lines - parse and compare with tolerance for numbers
                    if not self.compare_csv_data_lines(gen_line, exp_line, i+1):
                        return False, f"Data mismatch at line {i+1}"
            
            return True, "Files match"
            
        except Exception as e:
            return False, f"Error comparing files: {str(e)}"
    
    def compare_csv_data_lines(self, gen_line: str, exp_line: str, line_num: int) -> bool:
        """Compare CSV data lines with numerical tolerance"""
        try:
            gen_parts = [part.strip() for part in gen_line.split(',')]
            exp_parts = [part.strip() for part in exp_line.split(',')]
            
            if len(gen_parts) != len(exp_parts):
                return False
            
            for i, (gen_val, exp_val) in enumerate(zip(gen_parts, exp_parts)):
                # Try to parse as numbers for columns that should be numeric
                if i >= 7:  # Numeric columns (initial value, peak value, etc.)
                    try:
                        gen_num = float(gen_val)
                        exp_num = float(exp_val)
                        # Allow 1 INR tolerance for rounding differences
                        if abs(gen_num - exp_num) > 1:
                            return False
                    except ValueError:
                        # Not numeric, compare as strings
                        if gen_val != exp_val:
                            return False
                else:
                    # String comparison for non-numeric columns
                    if gen_val != exp_val:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def run_single_test(self, test_dir: Path) -> Dict:
        """Run a single test and return results"""
        test_name = test_dir.name
        year = self.get_test_year_from_config(test_dir)
        
        print(f"  Running {test_name} (year {year})...", end=" ")
        
        # Run FA calculator
        success, message = self.run_fa_calculator(test_dir, year)
        
        if not success:
            print(f"{Colors.RED}FAILED{Colors.NC}")
            return {
                'name': test_name,
                'status': 'FAILED',
                'reason': f"Calculator failed: {message}"
            }
        
        # Compare output
        generated_file = test_dir / "FA.csv"
        expected_file = test_dir / "expected_FA.csv"
        
        match_success, match_message = self.compare_csv_files(generated_file, expected_file)
        
        if match_success:
            print(f"{Colors.GREEN}PASSED{Colors.NC}")
            return {
                'name': test_name,
                'status': 'PASSED',
                'reason': 'Output matches expected'
            }
        else:
            print(f"{Colors.RED}FAILED{Colors.NC}")
            return {
                'name': test_name,
                'status': 'FAILED',
                'reason': f"Output mismatch: {match_message}"
            }
    
    def run_all_tests(self):
        """Run all core tests"""
        print(f"{Colors.BLUE}🧪 Running Core Tests for FA Calculator{Colors.NC}")
        print(f"Script: {self.fa_calculator}")
        print(f"Test directory: {self.core_tests_dir}")
        print()
        
        test_dirs = self.find_test_directories()
        
        if not test_dirs:
            print(f"{Colors.YELLOW}⚠️  No test directories found in {self.core_tests_dir}{Colors.NC}")
            return
        
        print(f"Found {len(test_dirs)} test directories:")
        
        for test_dir in test_dirs:
            result = self.run_single_test(test_dir)
            self.test_results.append(result)
            
            if result['status'] == 'PASSED':
                self.passed += 1
            else:
                self.failed += 1
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 60)
        print(f"{Colors.BLUE}📊 TEST SUMMARY{Colors.NC}")
        print("=" * 60)
        
        total = self.passed + self.failed
        print(f"Total tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.NC}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.NC}")
        
        if self.failed > 0:
            print()
            print(f"{Colors.RED}❌ FAILED TESTS:{Colors.NC}")
            for result in self.test_results:
                if result['status'] == 'FAILED':
                    print(f"  • {result['name']}: {result['reason']}")
        
        print()
        if self.failed == 0:
            print(f"{Colors.GREEN}🎉 All tests passed!{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}⚠️  {self.failed} test(s) failed{Colors.NC}")
            sys.exit(1)

def main():
    runner = CoreTestRunner()
    runner.run_all_tests()

if __name__ == "__main__":
    main()
