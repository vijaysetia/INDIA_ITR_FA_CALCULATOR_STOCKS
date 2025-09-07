#!/usr/bin/env python3
"""
Public Data Cache Cleanup Script
Python 3.7+ version of clean_up_public_data.sh

Granular control over cached public data cleanup.
"""

import json
import argparse
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class PublicDataCleanup:
    def __init__(self):
        self.public_data_file = Path("public_data.json")
        
    def show_header(self):
        """Display script header"""
        print(f"{Colors.BLUE}🧹 PUBLIC DATA CACHE CLEANER{Colors.NC}")
        print("Granular control over cached data cleanup")
        print()
    
    def load_public_data(self) -> Dict[str, Any]:
        """Load existing public data"""
        if not self.public_data_file.exists():
            print(f"{Colors.YELLOW}⚠️  {self.public_data_file} not found{Colors.NC}")
            return self.create_empty_structure()
        
        try:
            with open(self.public_data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Colors.RED}❌ Error reading {self.public_data_file}: {e}{Colors.NC}")
            return self.create_empty_structure()
    
    def save_public_data(self, data: Dict[str, Any]):
        """Save public data with sorting"""
        # Sort stocks alphabetically and dates chronologically
        sorted_data = {
            "stocks": {},
            "exchange_rates": dict(sorted(data.get("exchange_rates", {}).items())),
            "country_mapping": data.get("country_mapping", {
                "United States": 2,
                "United Kingdom": 3,
                "Canada": 4,
                "Germany": 5,
                "France": 6,
                "Japan": 7,
                "Australia": 8,
                "Netherlands": 9,
                "Switzerland": 10,
                "Singapore": 11
            })
        }
        
        # Sort stock data
        for symbol in sorted(data.get("stocks", {}).keys()):
            stock_data = data["stocks"][symbol]
            sorted_data["stocks"][symbol] = {
                "prices": dict(sorted(stock_data.get("prices", {}).items())),
                "company_info": stock_data.get("company_info", {}),
                "high_low": dict(sorted(stock_data.get("high_low", {}).items()))
            }
        
        with open(self.public_data_file, 'w') as f:
            json.dump(sorted_data, f, indent=2)
    
    def create_empty_structure(self) -> Dict[str, Any]:
        """Create empty public data structure"""
        return {
            "stocks": {},
            "exchange_rates": {},
            "country_mapping": {
                "United States": 2,
                "United Kingdom": 3,
                "Canada": 4,
                "Germany": 5,
                "France": 6,
                "Japan": 7,
                "Australia": 8,
                "Netherlands": 9,
                "Switzerland": 10,
                "Singapore": 11
            }
        }
    
    def create_sample_structure(self) -> Dict[str, Any]:
        """Create sample public data structure to show format"""
        return {
            "stocks": {
                "AAPL": {
                    "prices": {
                        "2024-01-02": 185.64,
                        "2024-01-03": 184.25
                    },
                    "company_info": {
                        "country": "United States",
                        "name": "Apple Inc.",
                        "address": "One Apple Park Way, Cupertino, CA",
                        "zip_code": "95014",
                        "nature": "Public Limited Company"
                    },
                    "high_low": {
                        "2024-01-02": {
                            "low": 183.89,
                            "high": 188.44
                        }
                    }
                }
            },
            "exchange_rates": {
                "2024-01-02": 83.25,
                "2024-01-03": 83.18
            },
            "country_mapping": {
                "United States": 2,
                "United Kingdom": 3,
                "Canada": 4,
                "Germany": 5,
                "France": 6,
                "Japan": 7,
                "Australia": 8,
                "Netherlands": 9,
                "Switzerland": 10,
                "Singapore": 11
            }
        }
    
    def create_backup(self) -> Optional[Path]:
        """Create backup of public data file"""
        if not self.public_data_file.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"public_data.json.backup_{timestamp}")
        
        try:
            shutil.copy2(self.public_data_file, backup_file)
            print(f"{Colors.GREEN}💾 Backup created: {backup_file}{Colors.NC}")
            return backup_file
        except IOError as e:
            print(f"{Colors.YELLOW}⚠️  Could not create backup: {e}{Colors.NC}")
            return None
    
    def get_confirmation(self, action_description: str) -> bool:
        """Get user confirmation for destructive action"""
        print(f"{Colors.YELLOW}⚠️  WARNING: This will delete {action_description}!{Colors.NC}")
        
        response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
        return response in ['y', 'yes']
    
    def delete_all_data(self):
        """Delete all public data and create sample data structure"""
        if not self.get_confirmation("all cached data (will create sample data structure)"):
            print(f"{Colors.GREEN}❌ Cleanup cancelled.{Colors.NC}")
            return
        
        backup_file = self.create_backup()
        
        # Create sample data structure instead of empty
        sample_data = self.create_sample_structure()
        self.save_public_data(sample_data)
        
        print(f"{Colors.GREEN}✅ All public data deleted and sample structure created{Colors.NC}")
        self.show_completion_message(backup_file)
    
    def delete_all_stocks(self):
        """Delete all stock-related data except UBER but keep exchange rates"""
        action_desc = "all stocks except UBER (keep exchange rates and UBER data)"
        
        if not self.get_confirmation(action_desc):
            print(f"{Colors.GREEN}❌ Cleanup cancelled.{Colors.NC}")
            return
        
        backup_file = self.create_backup()
        data = self.load_public_data()
        
        # Keep only UBER data
        stocks_data = data.get("stocks", {})
        uber_data = stocks_data.get("UBER", {}) if "UBER" in stocks_data else {}
        
        cleaned_data = {
            "stocks": {"UBER": uber_data} if uber_data else {},
            "exchange_rates": data.get("exchange_rates", {}),
            "country_mapping": data.get("country_mapping", {
                "United States": 2,
                "United Kingdom": 3,
                "Canada": 4,
                "Germany": 5,
                "France": 6,
                "Japan": 7,
                "Australia": 8,
                "Netherlands": 9,
                "Switzerland": 10,
                "Singapore": 11
            })
        }
        
        self.save_public_data(cleaned_data)
        
        print(f"{Colors.GREEN}✅ All stocks except UBER deleted (exchange rates and UBER data preserved){Colors.NC}")
        
        self.show_completion_message(backup_file)
    
    def delete_exchange_rates(self):
        """Delete only exchange rate data"""
        if not self.get_confirmation("exchange rates data (keep stocks)"):
            print(f"{Colors.GREEN}❌ Cleanup cancelled.{Colors.NC}")
            return
        
        backup_file = self.create_backup()
        data = self.load_public_data()
        
        # Keep only stocks data
        cleaned_data = {
            "stocks": data.get("stocks", {}),
            "exchange_rates": {},
            "country_mapping": data.get("country_mapping", {
                "United States": 2,
                "United Kingdom": 3,
                "Canada": 4,
                "Germany": 5,
                "France": 6,
                "Japan": 7,
                "Australia": 8,
                "Netherlands": 9,
                "Switzerland": 10,
                "Singapore": 11
            })
        }
        
        self.save_public_data(cleaned_data)
        
        print(f"{Colors.GREEN}✅ Exchange rates data deleted (stocks preserved){Colors.NC}")
        self.show_completion_message(backup_file)
    
    def delete_stock_data(self, stock_symbol: str):
        """Delete data for a specific stock symbol"""
        data = self.load_public_data()
        stocks = data.get("stocks", {})
        
        if stock_symbol not in stocks:
            print(f"{Colors.RED}❌ Stock symbol '{stock_symbol}' not found in cache{Colors.NC}")
            print(f"{Colors.BLUE}💡 Available symbols: {', '.join(sorted(stocks.keys())) if stocks else 'None'}{Colors.NC}")
            return
        
        if not self.get_confirmation(f"cached data for {stock_symbol}"):
            print(f"{Colors.GREEN}❌ Cleanup cancelled.{Colors.NC}")
            return
        
        backup_file = self.create_backup()
        
        # Remove the specific stock
        del data["stocks"][stock_symbol]
        
        self.save_public_data(data)
        
        print(f"{Colors.GREEN}✅ Data for {stock_symbol} deleted{Colors.NC}")
        self.show_completion_message(backup_file)
    
    def show_completion_message(self, backup_file: Optional[Path]):
        """Show completion message with next steps"""
        print()
        print(f"{Colors.YELLOW}💡 Next steps:{Colors.NC}")
        print("  1. Run fa_calculator.py to fetch new data")
        print("  2. Data fetched from internet will be shown in RED")
        print("  3. Future runs will use cached data (shown in GREEN)")
        
        if backup_file:
            print()
            print(f"{Colors.BLUE}💾 Backup information:{Colors.NC}")
            print(f"  • Backup saved as: {backup_file}")
            print(f"  • Restore with: mv {backup_file} {self.public_data_file}")
        
        print()
        print(f"{Colors.BLUE}📖 Data structure:{Colors.NC}")
        print("  - stocks.<SYMBOL>.company_info: Company details")
        print("  - stocks.<SYMBOL>.prices: Historical stock prices")
        print("  - exchange_rates: USD to INR rates by date")
    
    def show_help(self):
        """Show help message"""
        print(f"{Colors.BLUE}Usage: python3 clean_up_public_data.py [OPTIONS] [STOCK_SYMBOL]{Colors.NC}")
        print()
        print("OPTIONS:")
        print("  -a, --all         Delete all public data and create sample structure")
        print("  -s, --stocks      Delete all stocks data except UBER (keep exchange rates)")
        print("  -x, --exchange    Delete exchange rates data (keep stocks)")
        print("  -h, --help        Show this help message")
        print()
        print("STOCK_SYMBOL:")
        print("  Specific stock symbol to delete (e.g., AAPL, MSFT)")
        print("  If provided, only that stock's data will be deleted")
        print()
        print("EXAMPLES:")
        print("  python3 clean_up_public_data.py -a                    # Delete all data, create sample")
        print("  python3 clean_up_public_data.py -s                    # Delete all stocks except UBER")
        print("  python3 clean_up_public_data.py -x                    # Delete exchange rates")
        print("  python3 clean_up_public_data.py AAPL                 # Delete only AAPL stock data")
        print("  python3 clean_up_public_data.py -h                    # Show help")
        print()
        print("INVALID COMBINATIONS:")
        print("  python3 clean_up_public_data.py -a -s                # -a cannot be combined with other options")
        print("  python3 clean_up_public_data.py -x AAPL              # Exchange rates are not stock-specific")
        print("  python3 clean_up_public_data.py -s -x                # Use -a to delete everything instead")
    
    def validate_options(self, args) -> bool:
        """Validate command line options"""
        # Check for conflicting options
        if args.all and (args.stocks or args.exchange or args.stock_symbol):
            print(f"{Colors.RED}❌ -a/--all cannot be combined with other options.{Colors.NC}")
            return False
        
        if args.exchange and args.stock_symbol:
            print(f"{Colors.RED}❌ -x/--exchange cannot be combined with stock symbol.{Colors.NC}")
            print(f"{Colors.YELLOW}💡 Exchange rates are not stock-specific.{Colors.NC}")
            return False
        
        if args.stocks and args.exchange:
            print(f"{Colors.RED}❌ -s/--stocks and -x/--exchange cannot be combined. Use -a/--all to delete everything.{Colors.NC}")
            return False
        
        # Check if any action is specified
        if not (args.all or args.stocks or args.exchange or args.stock_symbol):
            print(f"{Colors.RED}❌ No action specified.{Colors.NC}")
            return False
        
        return True
    
    def run(self, args):
        """Main execution function"""
        self.show_header()
        
        # Validate options
        if not self.validate_options(args):
            self.show_help()
            sys.exit(1)
        
        # Execute the appropriate action
        if args.all:
            self.delete_all_data()
        elif args.exchange:
            self.delete_exchange_rates()
        elif args.stocks and args.stock_symbol:
            # -s with stock symbol: delete specific stock (same as just stock symbol)
            print(f"{Colors.BLUE}ℹ️  -s with stock symbol: deleting specific stock data for {args.stock_symbol}{Colors.NC}")
            self.delete_stock_data(args.stock_symbol)
        elif args.stocks:
            self.delete_all_stocks()
        elif args.stock_symbol:
            self.delete_stock_data(args.stock_symbol)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Granular control over cached public data cleanup",
        add_help=False  # We'll handle help ourselves
    )
    
    parser.add_argument('-a', '--all', action='store_true',
                       help='Delete all public data (stocks + exchange rates)')
    parser.add_argument('-s', '--stocks', action='store_true',
                       help='Delete all stocks data (keep exchange rates)')
    parser.add_argument('-x', '--exchange', action='store_true',
                       help='Delete exchange rates data (keep stocks)')
    parser.add_argument('-h', '--help', action='store_true',
                       help='Show this help message')
    parser.add_argument('stock_symbol', nargs='?',
                       help='Specific stock symbol to delete (e.g., AAPL, MSFT)')
    
    args = parser.parse_args()
    
    # Handle help
    if args.help:
        cleanup = PublicDataCleanup()
        cleanup.show_help()
        sys.exit(0)
    
    # Run cleanup
    cleanup = PublicDataCleanup()
    cleanup.run(args)


if __name__ == "__main__":
    main()
