#!/usr/bin/env python3
"""
Options Test Runner for FA Calculator

This script tests various command-line options and behaviors of the FA calculator
while using --no-internet to ensure fast, reproducible tests.

Tests focus on:
- Command-line argument parsing
- Option combinations
- Error handling
- Output behaviors
- File handling options
"""

import subprocess
import sys
import os
import json
import shutil
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Dict, Any

class OptionsTestRunner:
    def __init__(self):
        self.script_dir = Path(__file__).parent.parent.parent.absolute()  # Project root
        self.fa_calculator = self.script_dir / "fa_calculator.py"
        self.clean_up_pii = self.script_dir / "clean_up_pii.py"
        self.options_tests_dir = Path(__file__).parent
        self.test_data_dir = self.options_tests_dir / "test_data"
        
        # Test results
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
    def setup_test_data(self):
        """Create test data directory with sample files"""
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create sample vest.json
        vest_data = {
            "TEST": {
                "vests": [
                    {
                        "vest_date": "2023-01-15",
                        "number_of_shares": 50
                    }
                ]
            }
        }
        
        with open(self.test_data_dir / "vest.json", 'w') as f:
            json.dump(vest_data, f, indent=2)
            
        # Create empty sell.json
        with open(self.test_data_dir / "sell.json", 'w') as f:
            json.dump({}, f, indent=2)
            
        # Create public_data.json with comprehensive daily test data
        # Generate daily prices for the entire year
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        current_date = start_date
        prices = {}
        
        base_price = 100.0
        while current_date <= end_date:
            # Simple price variation: slight upward trend with some volatility
            days_from_start = (current_date - start_date).days
            trend_price = base_price + (days_from_start * 0.02)  # Small upward trend
            
            # Add some volatility (±2%)
            random.seed(current_date.toordinal())  # Deterministic randomness
            volatility = random.uniform(-2, 2)
            final_price = trend_price + volatility
            
            prices[current_date.strftime("%Y-%m-%d")] = f"{final_price:.2f}"
            current_date += timedelta(days=1)
        
        public_data = {
            "stocks": {
                "TEST": {
                    "prices": prices,
                    "company_info": {
                        "country": "United States",
                        "name": "Test Corp",
                        "address": "123 Test St",
                        "zip_code": "12345",
                        "nature": "Public Limited Company"
                    },
                    "high_low": {
                        "2023-01-15": {
                            "low": "104.00",
                            "high": "106.00"
                        }
                    }
                }
            },
            "exchange_rates": {
                "2023-01-01": "82.50",
                "2023-01-15": "82.75",
                "2023-02-01": "82.80",
                "2023-03-01": "82.90",
                "2023-04-01": "83.00",
                "2023-05-01": "83.10",
                "2023-06-01": "83.25",
                "2023-07-01": "83.30",
                "2023-08-01": "83.20",
                "2023-09-01": "83.15",
                "2023-10-01": "83.10",
                "2023-11-01": "83.05",
                "2023-12-31": "83.00"
            },
            "country_mapping": {
                "United States": 2
            }
        }
        
        with open(self.test_data_dir / "public_data.json", 'w') as f:
            json.dump(public_data, f, indent=2)
    
    def run_command(self, cmd: List[str], expect_success: bool = True) -> Tuple[bool, str, str]:
        """Run a command and return (success, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = (result.returncode == 0) == expect_success
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def test_help_option(self) -> bool:
        """Test --help option"""
        cmd = ["python3", str(self.fa_calculator), "--help"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Check that help contains expected sections
        help_sections = ["usage:", "positional arguments:", "optional arguments:"]
        return all(section in stdout.lower() for section in help_sections)
    
    def test_verbose_option(self) -> bool:
        """Test -v/--verbose option"""
        cmd = ["python3", str(self.fa_calculator), "--data", str(self.test_data_dir), 
               "2023", "--no-internet", "-v"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Verbose should show more detailed output
        verbose_indicators = ["Step 1:", "Step 2:", "Step 3:", "Step 4:"]
        return any(indicator in stdout for indicator in verbose_indicators)
    
    def test_skip_validation_option(self) -> bool:
        """Test -x (skip validation) option"""
        cmd = ["python3", str(self.fa_calculator), "--data", str(self.test_data_dir),
               "2023", "--no-internet", "-x"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Should complete successfully and generate FA.csv
        fa_csv = self.test_data_dir / "FA.csv"
        return fa_csv.exists()
    
    def test_skip_sorting_option(self) -> bool:
        """Test -y (skip sorting) option"""
        cmd = ["python3", str(self.fa_calculator), "--data", str(self.test_data_dir),
               "2023", "--no-internet", "-y"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Should show "Skipping data file sorting"
        return "Skipping data file sorting" in stdout
    
    def test_data_option(self) -> bool:
        """Test --data option with custom directory"""
        # Create a separate test directory
        custom_dir = self.options_tests_dir / "custom_test_data"
        if custom_dir.exists():
            shutil.rmtree(custom_dir)
        custom_dir.mkdir()
        
        # Copy test data to custom directory
        shutil.copy2(self.test_data_dir / "vest.json", custom_dir)
        shutil.copy2(self.test_data_dir / "sell.json", custom_dir)
        shutil.copy2(self.test_data_dir / "public_data.json", custom_dir)
        
        cmd = ["python3", str(self.fa_calculator), "--data", str(custom_dir),
               "2023", "--no-internet", "-x", "-y"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Should create FA.csv in the custom directory
        fa_csv = custom_dir / "FA.csv"
        result = fa_csv.exists()
        
        # Cleanup
        shutil.rmtree(custom_dir)
        return result
    
    def test_invalid_year(self) -> bool:
        """Test invalid year argument"""
        cmd = ["python3", str(self.fa_calculator), "--data", str(self.test_data_dir),
               "invalid_year", "--no-internet"]
        success, stdout, stderr = self.run_command(cmd, expect_success=False)
        
        # Should fail and show error message
        return success and ("invalid" in stderr.lower() or "error" in stdout.lower())
    
    def test_missing_data_directory(self) -> bool:
        """Test --data with non-existent directory"""
        cmd = ["python3", str(self.fa_calculator), "--data", "/non/existent/path",
               "2023", "--no-internet"]
        success, stdout, stderr = self.run_command(cmd, expect_success=False)
        
        # Should fail with appropriate error
        return success
    
    def test_combined_options(self) -> bool:
        """Test combination of multiple options"""
        cmd = ["python3", str(self.fa_calculator), "--data", str(self.test_data_dir),
               "2023", "--no-internet", "-v", "-x", "-y"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Should show verbose output and skipping messages
        return ("Step 1:" in stdout and 
                "Skipping data file sorting" in stdout and
                (self.test_data_dir / "FA.csv").exists())
    
    def test_clean_up_pii_help(self) -> bool:
        """Test clean_up_pii.py --help"""
        cmd = ["python3", str(self.clean_up_pii), "--help"]
        success, stdout, stderr = self.run_command(cmd)
        
        if not success:
            return False
            
        # Check that help contains expected content
        return "Remove personal transaction data" in stdout
    
    def test_clean_up_pii_data_option(self) -> bool:
        """Test clean_up_pii.py --data option (dry run style)"""
        # Create a copy of test data for cleanup test
        cleanup_dir = self.options_tests_dir / "cleanup_test_data"
        if cleanup_dir.exists():
            shutil.rmtree(cleanup_dir)
        cleanup_dir.mkdir()
        
        shutil.copy2(self.test_data_dir / "vest.json", cleanup_dir)
        shutil.copy2(self.test_data_dir / "sell.json", cleanup_dir)
        
        # Test that the script recognizes the --data option (we won't actually run cleanup)
        cmd = ["python3", str(self.clean_up_pii), "--data", str(cleanup_dir), "--help"]
        success, stdout, stderr = self.run_command(cmd)
        
        # Cleanup
        shutil.rmtree(cleanup_dir)
        
        return success and "--data" in stdout
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results"""
        print(f"  Running {test_name}...", end=" ")
        
        try:
            result = test_func()
            if result:
                print("PASSED")
                self.passed_tests += 1
                self.test_results.append((test_name, "PASSED", ""))
                return True
            else:
                print("FAILED")
                self.failed_tests += 1
                self.test_results.append((test_name, "FAILED", "Test assertion failed"))
                return False
        except Exception as e:
            print(f"FAILED ({str(e)})")
            self.failed_tests += 1
            self.test_results.append((test_name, "FAILED", str(e)))
            return False
    
    def cleanup_test_data(self):
        """Clean up test data files"""
        if self.test_data_dir.exists():
            # Remove generated files but keep the directory structure
            for file in ["FA.csv"]:
                file_path = self.test_data_dir / file
                if file_path.exists():
                    file_path.unlink()
    
    def run_all_tests(self):
        """Run all option tests"""
        print("🧪 Running Options Tests for FA Calculator")
        print(f"Script: {self.fa_calculator}")
        print(f"Test directory: {self.options_tests_dir}")
        print()
        
        # Setup test data
        self.setup_test_data()
        
        # Define tests
        tests = [
            ("help_option", self.test_help_option),
            ("verbose_option", self.test_verbose_option),
            ("skip_validation_option", self.test_skip_validation_option),
            ("skip_sorting_option", self.test_skip_sorting_option),
            ("data_option", self.test_data_option),
            ("invalid_year", self.test_invalid_year),
            ("missing_data_directory", self.test_missing_data_directory),
            ("combined_options", self.test_combined_options),
            ("clean_up_pii_help", self.test_clean_up_pii_help),
            ("clean_up_pii_data_option", self.test_clean_up_pii_data_option),
        ]
        
        # Run tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Print summary
        print()
        print("=" * 60)
        print("📊 OPTIONS TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        
        if self.failed_tests > 0:
            print()
            print("❌ FAILED TESTS:")
            for test_name, status, error in self.test_results:
                if status == "FAILED":
                    print(f"  • {test_name}: {error}")
            print()
            print(f"⚠️  {self.failed_tests} test(s) failed")
            return False
        else:
            print()
            print("🎉 All tests passed!")
            return True

def main():
    runner = OptionsTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
