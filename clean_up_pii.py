#!/usr/bin/env python3
"""
PII Data Cleanup Script
Python 3.7+ version of clean_up_pii.sh

This script removes personal transaction data while maintaining file structure.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class PIICleanup:
    def __init__(self, data_dir: str = None):
        # Set data directory - default to script directory
        if data_dir is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.absolute()
            self.data_dir = script_dir
        else:
            self.data_dir = Path(data_dir)
            
        self.vest_file = self.data_dir / "vest.json"
        self.sell_file = self.data_dir / "sell.json"
        self.fa_csv = self.data_dir / "FA.csv"
        
    def show_warning(self):
        """Display critical warning messages"""
        print(f"{Colors.RED}{'='*60}{Colors.NC}")
        print(f"{Colors.RED}🚨 CRITICAL WARNING - PII DATA DELETION 🚨{Colors.NC}")
        print(f"{Colors.RED}{'='*60}{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}⚠️  This script will PERMANENTLY DELETE your personal transaction data:{Colors.NC}")
        print(f"   • {self.vest_file} - Your stock vest records")
        print(f"   • {self.sell_file} - Your stock sale records") 
        print(f"   • {self.fa_csv} - Your calculated FA schedule")
        print()
        print(f"{Colors.RED}🔥 NO BACKUPS WILL BE CREATED{Colors.NC}")
        print(f"{Colors.RED}🔥 THIS ACTION CANNOT BE UNDONE{Colors.NC}")
        print(f"{Colors.RED}🔥 ALL YOUR TRANSACTION DATA WILL BE LOST{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}📋 What will remain:{Colors.NC}")
        print("   • Template structure for JSON files")
        print("   • CSV header for FA calculations")
        print("   • public_data.json (market data cache)")
        print()
        print(f"{Colors.RED}{'='*60}{Colors.NC}")
        print()
    
    def get_confirmation(self) -> bool:
        """Get double confirmation from user"""
        print(f"{Colors.YELLOW}🤔 Are you absolutely sure you want to delete all PII data?{Colors.NC}")
        print("Type 'yes' to continue or anything else to cancel:")
        
        first_response = input().strip().lower()
        if first_response != 'yes':
            print(f"{Colors.GREEN}✅ Cleanup cancelled. Your data is safe.{Colors.NC}")
            return False
        
        print()
        print(f"{Colors.RED}🔐 FINAL CONFIRMATION REQUIRED{Colors.NC}")
        print(f"{Colors.RED}This is your last chance to prevent data loss!{Colors.NC}")
        print()
        print(f"To proceed with PII deletion, type exactly: {Colors.YELLOW}DELETE_MY_PII{Colors.NC}")
        print("Type anything else to cancel:")
        
        confirmation_code = input().strip()
        if confirmation_code != "DELETE_MY_PII":
            print(f"{Colors.GREEN}✅ Cleanup cancelled. Your data is safe.{Colors.NC}")
            return False
        
        return True
    
    def create_vest_template(self) -> Dict[str, Any]:
        """Create template structure based on current vest.json"""
        try:
            # Load current vest.json
            with open(self.vest_file, 'r') as f:
                current_data = json.load(f)
            
            # Keep only UBER data, set all share counts to 0
            if "UBER" in current_data:
                uber_data = current_data["UBER"]
                if "vests" in uber_data:
                    # Set all share counts to 0
                    for vest in uber_data["vests"]:
                        vest["number_of_shares"] = 0
                
                return {"UBER": uber_data}
            else:
                # No UBER data found, return empty
                return {}
                
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to template structure if file doesn't exist or is invalid
            return {
                "UBER": {
                    "vests": [
                        {
                            "vest_date": "2024-01-16",
                            "number_of_shares": 0
                        }
                    ]
                }
            }
    
    def create_sell_template(self) -> Dict[str, Any]:
        """Create template structure for sell.json based on current data"""
        try:
            # Load current sell.json if it exists
            if self.sell_file.exists():
                with open(self.sell_file, 'r') as f:
                    current_data = json.load(f)
                
                # Keep only UBER data, set all share counts to 1 for template
                if "UBER" in current_data:
                    uber_data = current_data["UBER"]
                    if "sales" in uber_data and uber_data["sales"]:
                        # Use first sale as template, set to 1 share
                        first_sale = uber_data["sales"][0].copy()
                        first_sale["number_of_shares_sold"] = 1
                        first_sale["sell_price_inr"] = 5000.0  # Template value
                        
                        return {"UBER": {"sales": [first_sale]}}
                    else:
                        # No sales data, create template sale
                        return self._create_uber_sale_template()
                else:
                    # No UBER data found, create template
                    return self._create_uber_sale_template()
            else:
                # No sell file exists, create UBER template
                return self._create_uber_sale_template()
                
        except json.JSONDecodeError:
            # Invalid JSON, create template
            return self._create_uber_sale_template()
    
    def _create_uber_sale_template(self) -> Dict[str, Any]:
        """Create a template UBER sale transaction"""
        return {
            "UBER": {
                "sales": [
                    {
                        "sell_date": "2024-06-15",
                        "vest_date": "2024-01-16", 
                        "number_of_shares_sold": 1,
                        "sell_price_inr": 5000.0
                    }
                ]
            }
        }
    
    def create_fa_csv_template(self) -> str:
        """Create template CSV header"""
        return (
            "Country/Region,Country Code,Name of entity,Address,ZIP Code,"
            "Nature of entity,Date of acquiring interest,Initial value of investment,"
            "Peak value of investment during the Period,Closing balance,"
            "Total gross amount paid,Total gross proceeds\n"
        )
    
    def cleanup_files(self):
        """Clean up all PII files and create templates"""
        files_processed = []
        
        # Clean up vest.json
        if self.vest_file.exists():
            print(f"{Colors.YELLOW}🗑️  Cleaning {self.vest_file}...{Colors.NC}")
            template = self.create_vest_template()
            with open(self.vest_file, 'w') as f:
                json.dump(template, f, indent=2)
            files_processed.append(str(self.vest_file))
        else:
            print(f"{Colors.BLUE}ℹ️  {self.vest_file} not found, creating template...{Colors.NC}")
            template = self.create_vest_template()
            with open(self.vest_file, 'w') as f:
                json.dump(template, f, indent=2)
            files_processed.append(f"{self.vest_file} (created)")
        
        # Clean up sell.json
        if self.sell_file.exists():
            print(f"{Colors.YELLOW}🗑️  Cleaning {self.sell_file}...{Colors.NC}")
            template = self.create_sell_template()
            with open(self.sell_file, 'w') as f:
                json.dump(template, f, indent=2)
            files_processed.append(str(self.sell_file))
        else:
            print(f"{Colors.BLUE}ℹ️  {self.sell_file} not found, creating template...{Colors.NC}")
            template = self.create_sell_template()
            with open(self.sell_file, 'w') as f:
                json.dump(template, f, indent=2)
            files_processed.append(f"{self.sell_file} (created)")
        
        # Clean up FA.csv
        if self.fa_csv.exists():
            print(f"{Colors.YELLOW}🗑️  Cleaning {self.fa_csv}...{Colors.NC}")
            with open(self.fa_csv, 'w') as f:
                f.write(self.create_fa_csv_template())
            files_processed.append(str(self.fa_csv))
        else:
            print(f"{Colors.BLUE}ℹ️  {self.fa_csv} not found, creating template...{Colors.NC}")
            with open(self.fa_csv, 'w') as f:
                f.write(self.create_fa_csv_template())
            files_processed.append(f"{self.fa_csv} (created)")
        
        return files_processed
    
    def show_completion_message(self, files_processed: list):
        """Show completion message with summary"""
        print()
        print(f"{Colors.GREEN}{'='*50}{Colors.NC}")
        print(f"{Colors.GREEN}✅ PII CLEANUP COMPLETED{Colors.NC}")
        print(f"{Colors.GREEN}{'='*50}{Colors.NC}")
        print()
        print(f"{Colors.GREEN}📋 Files processed:{Colors.NC}")
        for file_info in files_processed:
            print(f"   ✓ {file_info}")
        print()
        print(f"{Colors.YELLOW}📝 What happened:{Colors.NC}")
        print("   • All personal transaction data has been removed")
        print("   • Template structures have been created")
        print("   • You can now safely share these files")
        print()
        print(f"{Colors.BLUE}💡 Next steps:{Colors.NC}")
        print("   1. Add your actual transaction data to the template files")
        print("   2. Run fa_calculator.py to generate FA schedule")
        print("   3. The public_data.json cache remains intact for faster processing")
        print()
        print(f"{Colors.YELLOW}⚠️  Remember: This cleanup removed your actual data!{Colors.NC}")
        print(f"{Colors.YELLOW}   Make sure you have your transaction records elsewhere.{Colors.NC}")
    
    def run(self):
        """Main execution function"""
        print(f"{Colors.BLUE}🧹 PII DATA CLEANUP UTILITY{Colors.NC}")
        print("Removes personal transaction data while maintaining file structure")
        print()
        
        # Show warning
        self.show_warning()
        
        # Get confirmation
        if not self.get_confirmation():
            return
        
        print()
        print(f"{Colors.RED}🔥 PROCEEDING WITH PII DATA DELETION...{Colors.NC}")
        print()
        
        try:
            # Clean up files
            files_processed = self.cleanup_files()
            
            # Show completion message
            self.show_completion_message(files_processed)
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error during cleanup: {e}{Colors.NC}")
            print(f"{Colors.RED}Some files may have been partially processed.{Colors.NC}")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Remove personal transaction data while maintaining file structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 clean_up_pii.py           # Clean script directory (default)
  python3 clean_up_pii.py --data ./data  # Clean specific data directory
        """
    )
    
    parser.add_argument('--data', default=None,
                       help='Data directory containing vest.json, sell.json, FA.csv (default: script directory)')
    
    args = parser.parse_args()
    
    cleanup = PIICleanup(data_dir=args.data)
    cleanup.run()


if __name__ == "__main__":
    main()
