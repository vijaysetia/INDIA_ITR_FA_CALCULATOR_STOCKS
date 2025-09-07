#!/usr/bin/env python3
"""
Foreign Assets Schedule Calculator for ITR
Python 3.7+ version of fa_calculator.sh

Usage: python3 fa_calculator.py [OPTIONS] <year>
"""

# Suppress warnings before importing anything
import warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL.*')

import json
import requests
import argparse
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv
from io import StringIO
import urllib3

# Disable urllib3 warnings
urllib3.disable_warnings()

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class FACalculator:
    def __init__(self, year: int, no_internet: bool = False, 
                 data_dir: str = None, verbose: bool = False,
                 exclude_validation: bool = False, no_sort: bool = False):
        self.year = year
        self.no_internet = no_internet
        self.verbose = verbose
        self.exclude_validation = exclude_validation
        self.no_sort = no_sort
        
        # Set data directory - default to script directory
        if data_dir is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.absolute()
            self.data_dir = script_dir
        else:
            self.data_dir = Path(data_dir)
            
        self.vest_file = self.data_dir / "vest.json"
        self.sell_file = self.data_dir / "sell.json"
        self.public_data_file = self.data_dir / "public_data.json"
        self.fa_csv = self.data_dir / "FA.csv"
        
        # Configuration
        self.fetch_delay_seconds = 0.1  # Minimal delay for better performance
        self.cache_update_interval = 10
        
        # Tracking for cache updates
        self.fetched_data = {
            'stock_prices': [],
            'exchange_rates': []
        }
        
        # Load existing data
        self.public_data = self.load_public_data()
    
    def vprint(self, message: str):
        """Print message only in verbose mode"""
        if self.verbose:
            print(message)
    
    def print_always(self, message: str):
        """Print message always (both verbose and non-verbose modes)"""
        print(message)
        
    def load_public_data(self) -> Dict:
        """Load existing public data from JSON file"""
        if self.public_data_file.exists():
            try:
                with open(self.public_data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"{Colors.YELLOW}⚠️  Warning: Could not load {self.public_data_file}: {e}{Colors.NC}")
        
        # Return empty structure
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
    
    def save_public_data(self):
        """Save public data to JSON file with sorting"""
        # Sort stocks alphabetically and dates chronologically
        sorted_data = {
            "stocks": {},
            "exchange_rates": dict(sorted(self.public_data.get("exchange_rates", {}).items())),
            "country_mapping": self.public_data.get("country_mapping", {
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
        for symbol in sorted(self.public_data.get("stocks", {}).keys()):
            stock_data = self.public_data["stocks"][symbol]
            sorted_data["stocks"][symbol] = {
                "prices": dict(sorted(stock_data.get("prices", {}).items())),
                "company_info": stock_data.get("company_info", {}),
                "high_low": dict(sorted(stock_data.get("high_low", {}).items()))
            }
        
        with open(self.public_data_file, 'w') as f:
            json.dump(sorted_data, f, indent=2)
        
        self.public_data = sorted_data
    
    def validate_year(self) -> bool:
        """Validate the input year"""
        self.vprint(f"{Colors.YELLOW}🔍 Validating year parameter: {self.year}{Colors.NC}")
        
        # Check if year is 4-digit number
        if not (1000 <= self.year <= 9999):
            print(f"{Colors.RED}❌ Error: Year must be a 4-digit number (e.g., {Colors.YELLOW}2024{Colors.RED}){Colors.NC}")
            return False
        
        # Check if year is not >= current year
        current_year = datetime.now().year
        if self.year >= current_year:
            print(f"{Colors.RED}❌ Error: Year cannot be greater than or equal to current year ({Colors.YELLOW}{current_year}{Colors.RED}){Colors.NC}")
            print(f"{Colors.RED}   Tax calculations are only valid for completed years.{Colors.NC}")
            return False
        
        # Check if year is not less than earliest vest year
        try:
            with open(self.vest_file, 'r') as f:
                vest_data = json.load(f)
            
            earliest_year = None
            for symbol_data in vest_data.values():
                for vest in symbol_data.get("vests", []):
                    vest_year = int(vest["vest_date"][:4])
                    if earliest_year is None or vest_year < earliest_year:
                        earliest_year = vest_year
            
            if earliest_year is None:
                print(f"{Colors.RED}❌ Error: No vest dates found in {self.vest_file}{Colors.NC}")
                return False
            
            if self.year < earliest_year:
                print(f"{Colors.RED}❌ Error: Year {Colors.YELLOW}{self.year}{Colors.RED} is earlier than the earliest vest date in {self.vest_file}{Colors.NC}")
                print(f"{Colors.RED}   Earliest vest year found: {Colors.YELLOW}{earliest_year}{Colors.NC}")
                print(f"{Colors.RED}   Please specify a year between {Colors.YELLOW}{earliest_year}{Colors.RED} and {Colors.YELLOW}{current_year - 1}{Colors.NC}")
                return False
        
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"{Colors.RED}❌ Error reading {self.vest_file}: {e}{Colors.NC}")
            return False
        
        self.vprint(f"{Colors.GREEN}✓ Year validation passed: {Colors.YELLOW}{self.year}{Colors.GREEN} is valid (range: {Colors.YELLOW}{earliest_year}{Colors.GREEN} to {Colors.YELLOW}{current_year - 1}{Colors.GREEN}){Colors.NC}")
        return True
    
    def get_stock_price(self, symbol: str, date: str) -> Optional[float]:
        """Get stock price for a symbol on a specific date"""
        # First, try to get price from cache
        cached_price = (self.public_data.get("stocks", {})
                       .get(symbol, {})
                       .get("prices", {})
                       .get(date))
        
        if cached_price is not None:
            return float(cached_price)
        
        # Check if no-internet mode is enabled
        if self.no_internet:
            print(f"{Colors.RED}❌ ERROR: Stock price for {symbol} on {date} not found in cache{Colors.NC}")
            print(f"{Colors.RED}   --no-internet mode enabled, cannot fetch from internet{Colors.NC}")
            print(f"{Colors.RED}   Please run without --no-internet to fetch missing data{Colors.NC}")
            return None
        
        # Fetch from internet
        self.vprint(f"{Colors.RED}🌐 FETCHING FROM INTERNET: {symbol} price for {date}{Colors.NC}")
        
        # Try multiple approaches for getting stock price
        for attempt in range(7):  # Try up to 7 days back for weekends/holidays
            temp_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=attempt)
            temp_date_str = temp_date.strftime("%Y-%m-%d")
            
            # Skip weekends
            if temp_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            price = self._fetch_yahoo_price(symbol, temp_date_str)
            if price is not None:
                formatted_price = round(price, 2)
                self.vprint(f"{Colors.RED}✓ Successfully fetched {symbol} price: {formatted_price} for {temp_date_str}{Colors.NC}")
                
                # Cache for both the actual date found AND the original requested date
                self._cache_stock_price(symbol, temp_date_str, formatted_price)
                if temp_date_str != date:
                    self._cache_stock_price(symbol, date, formatted_price)
                    self.vprint(f"{Colors.RED}✓ Caching {symbol} price {formatted_price} for original date {date} (using {temp_date_str} data){Colors.NC}")
                
                return formatted_price
        
        # Error out instead of using approximate prices
        print(f"{Colors.RED}❌ ERROR: Could not fetch stock price for {symbol} on {date}{Colors.NC}")
        print(f"{Colors.RED}   Unable to retrieve accurate price data from Yahoo Finance{Colors.NC}")
        print(f"{Colors.RED}   This may be due to rate limiting, network issues, or invalid date{Colors.NC}")
        print(f"{Colors.RED}   Please try again later or check your internet connection{Colors.NC}")
        return None
    
    def _fetch_yahoo_price(self, symbol: str, date: str) -> Optional[float]:
        """Fetch stock price for a specific date"""
        return self._fetch_single_day_price(symbol, date)
    
    def get_purchase_price_with_vest_override(self, symbol: str, date: str, vest_data: dict) -> Optional[float]:
        """Get purchase price, using vest_price if available (already validated), otherwise fallback to market data"""
        
        # Check if vest_price_optional is provided in the vest data
        vest_price = vest_data.get("vest_price_optional")
        
        if vest_price is not None:
            self.vprint(f"🎯 Using validated vest price for {symbol} {date}: ${vest_price}")
            return float(vest_price)
        
        # No vest_price provided, use regular market data
        return self.get_stock_price(symbol, date)
    
    def _cache_stock_price(self, symbol: str, date: str, price: float):
        """Cache a stock price"""
        if "stocks" not in self.public_data:
            self.public_data["stocks"] = {}
        if symbol not in self.public_data["stocks"]:
            self.public_data["stocks"][symbol] = {"prices": {}, "company_info": {}}
        if "prices" not in self.public_data["stocks"][symbol]:
            self.public_data["stocks"][symbol]["prices"] = {}
        
        self.public_data["stocks"][symbol]["prices"][date] = f"{price:.2f}"
        
        # Track for batch updates
        self.fetched_data['stock_prices'].append({
            'symbol': symbol,
            'date': date,
            'price': f"{price:.2f}"
        })
    
    def get_sbi_rate(self, date: str) -> Optional[float]:
        """Get SBI exchange rate for a specific date"""
        # First, try to get rate from cache
        cached_rate = self.public_data.get("exchange_rates", {}).get(date)
        
        if cached_rate is not None:
            return float(cached_rate)
        
        # Check if no-internet mode is enabled
        if self.no_internet:
            print(f"{Colors.RED}❌ ERROR: SBI exchange rate for {date} not found in cache{Colors.NC}")
            print(f"{Colors.RED}   --no-internet mode enabled, cannot fetch from internet{Colors.NC}")
            print(f"{Colors.RED}   Please run without --no-internet to fetch missing data{Colors.NC}")
            return None
        
        # Fetch from internet (silent)
        
        try:
            sbi_url = "https://raw.githubusercontent.com/sahilgupta/sbi-fx-ratekeeper/main/csv_files/SBI_REFERENCE_RATES_USD.csv"
            
            response = requests.get(sbi_url, timeout=30)
            response.raise_for_status()
            
            # Try to find exact date match first
            for line in response.text.split('\n'):
                if line.startswith(date):
                    parts = line.split(',')
                    if len(parts) >= 4:
                        try:
                            rate = float(parts[3])  # TT SELL rate (column 4)
                            if rate > 0:
                                self._cache_exchange_rate(date, rate)
                                return rate
                        except ValueError:
                            continue
            
            # Try previous dates (up to 10 days back)
            for days_back in range(1, 11):
                temp_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=days_back)
                temp_date_str = temp_date.strftime("%Y-%m-%d")
                
                for line in response.text.split('\n'):
                    if line.startswith(temp_date_str):
                        parts = line.split(',')
                        if len(parts) >= 4:
                            try:
                                rate = float(parts[3])
                                if rate > 0:
                                    self._cache_exchange_rate(date, rate)
                                    return rate
                            except ValueError:
                                continue
            
            # Use most recent rate as fallback
            lines = [line for line in response.text.split('\n') if line and not line.startswith('DATE')]
            if lines:
                last_line = lines[-1]
                parts = last_line.split(',')
                if len(parts) >= 4:
                    try:
                        rate = float(parts[3])
                        if rate > 0:
                            print(f"{Colors.RED}✓ Using most recent SBI rate for {date}: ₹{rate}{Colors.NC}")
                            self._cache_exchange_rate(date, rate)
                            return rate
                    except ValueError:
                        pass
        
        except requests.RequestException as e:
            print(f"Error fetching SBI rate: {e}")
        
        # Historical fallback based on year
        year = int(date[:4])
        fallback_rates = {
            2024: 83.0,
            2023: 82.0,
            2022: 79.0,
            2021: 74.0,
            2020: 75.0
        }
        
        fallback_rate = fallback_rates.get(year, 80.0)
        print(f"{Colors.RED}⚠ Using historical fallback rate for {date}: ₹{fallback_rate}{Colors.NC}")
        self._cache_exchange_rate(date, fallback_rate)
        return fallback_rate
    
    def _cache_exchange_rate(self, date: str, rate: float):
        """Cache an exchange rate and save immediately"""
        if "exchange_rates" not in self.public_data:
            self.public_data["exchange_rates"] = {}
        
        self.public_data["exchange_rates"][date] = f"{rate:.2f}"
        
        # Save to file immediately
        self._save_cache_silently()
    
    def get_company_info(self, symbol: str) -> Dict[str, str]:
        """Get company information for a symbol"""
        # First, try to get info from cache
        cached_info = (self.public_data.get("stocks", {})
                      .get(symbol, {})
                      .get("company_info", {}))
        
        if cached_info and cached_info.get("name"):
            return {
                'country': cached_info.get('country', 'United States'),
                'name': cached_info.get('name', f'{symbol} Inc.'),
                'address': cached_info.get('address', 'N/A'),
                'zip_code': cached_info.get('zip_code', 'N/A'),
                'nature': cached_info.get('nature', 'Public Company')
            }
        
        # Check if no-internet mode is enabled
        if self.no_internet:
            print(f"{Colors.RED}❌ ERROR: Company info for {symbol} not found in cache{Colors.NC}")
            print(f"{Colors.RED}   --no-internet mode enabled, cannot fetch from internet{Colors.NC}")
            print(f"{Colors.RED}   Please run without --no-internet to fetch missing data{Colors.NC}")
            return self._get_default_company_info(symbol)
        
        # Try to fetch from internet first
        company_info = self._fetch_company_info_from_internet(symbol)
        if company_info:
            self._cache_company_info(symbol, company_info)
            return company_info
        
        # Fallback to enhanced company info
        company_info = self._get_enhanced_company_info(symbol)
        self._cache_company_info(symbol, company_info)
        return company_info
    
    def _fetch_company_info_from_internet(self, symbol: str) -> Dict[str, str]:
        """Fetch company information from Yahoo Finance with proper authentication"""
        try:
            # First, get a crumb by visiting Yahoo Finance
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Get crumb from Yahoo Finance
            crumb_url = f"https://finance.yahoo.com/quote/{symbol}"
            crumb_response = session.get(crumb_url, timeout=10)
            crumb_response.raise_for_status()
            
            # Extract crumb from the page
            import re
            crumb_match = re.search(r'"CrumbStore":\{"crumb":"([^"]+)"\}', crumb_response.text)
            if not crumb_match:
                return None
            
            crumb = crumb_match.group(1)
            
            # Now use the crumb to get company info
            yahoo_url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=assetProfile&crumb={crumb}"
            
            response = session.get(yahoo_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            profile = data.get('quoteSummary', {}).get('result', [{}])[0].get('assetProfile', {})
            
            if profile:
                company_info = {
                    'country': profile.get('country', 'United States'),
                    'name': profile.get('longName') or profile.get('shortName', f'{symbol} Inc.'),
                    'address': self._build_address(profile),
                    'zip_code': profile.get('zip', 'N/A'),
                    'nature': profile.get('sector', 'Public Limited Company')
                }
                
                self.vprint(f"📊 Fetched company info for {symbol} from internet")
                return company_info
        
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Could not fetch company info for {symbol} from internet: {e}{Colors.NC}")
            return None
        
        return None
    
    def _build_address(self, profile: Dict) -> str:
        """Build address string from profile data"""
        address_parts = []
        
        if profile.get('address1'):
            address_parts.append(profile['address1'])
        if profile.get('city'):
            address_parts.append(profile['city'])
        if profile.get('state'):
            address_parts.append(profile['state'])
        
        return ' '.join(address_parts) if address_parts else 'N/A'
    
    def _get_default_company_info(self, symbol: str) -> Dict[str, str]:
        """Get default company info for a symbol"""
        return {
            'country': 'United States',
            'name': f'{symbol} Inc.',
            'address': 'N/A',
            'zip_code': 'N/A',
            'nature': 'Public Company'
        }
    
    def _get_enhanced_company_info(self, symbol: str) -> Dict[str, str]:
        """Get enhanced company information with known details for common stocks"""
        # Enhanced info for common US stocks
        company_data = {
            'AAPL': {
                'name': 'Apple Inc.',
                'address': 'One Apple Park Way Cupertino CA',
                'zip_code': '95014',
                'nature': 'Public Limited Company'
            },
            'MSFT': {
                'name': 'Microsoft Corporation',
                'address': 'One Microsoft Way Redmond WA',
                'zip_code': '98052',
                'nature': 'Public Limited Company'
            },
            'AMZN': {
                'name': 'Amazon.com Inc.',
                'address': '410 Terry Avenue North Seattle WA',
                'zip_code': '98109',
                'nature': 'Public Limited Company'
            },
            'GOOG': {
                'name': 'Alphabet Inc.',
                'address': '1600 Amphitheatre Parkway Mountain View CA',
                'zip_code': '94043',
                'nature': 'Public Limited Company'
            },
            'GOOGL': {
                'name': 'Alphabet Inc.',
                'address': '1600 Amphitheatre Parkway Mountain View CA',
                'zip_code': '94043',
                'nature': 'Public Limited Company'
            },
            'TSLA': {
                'name': 'Tesla Inc.',
                'address': '1 Tesla Road Austin TX',
                'zip_code': '78725',
                'nature': 'Public Limited Company'
            },
            'NVDA': {
                'name': 'NVIDIA Corporation',
                'address': '2788 San Tomas Expressway Santa Clara CA',
                'zip_code': '95051',
                'nature': 'Public Limited Company'
            },
            'META': {
                'name': 'Meta Platforms Inc.',
                'address': '1 Meta Way Menlo Park CA',
                'zip_code': '94025',
                'nature': 'Public Limited Company'
            },
            'UBER': {
                'name': 'Uber Technologies Inc.',
                'address': '1515 3rd Street San Francisco CA',
                'zip_code': '94158',
                'nature': 'Public Limited Company'
            },
            'SNAP': {
                'name': 'Snap Inc.',
                'address': '2772 Donald Douglas Loop North Santa Monica CA',
                'zip_code': '90405',
                'nature': 'Public Limited Company'
            }
        }
        
        if symbol in company_data:
            info = company_data[symbol].copy()
            info.update({
                'country': 'United States'
            })
            return info
        else:
            # Print error for unknown symbols and use sample info
            print(f"{Colors.RED}❌ ERROR: No company data available for {symbol}{Colors.NC}")
            print(f"{Colors.RED}   Using sample company information. Please verify details manually.{Colors.NC}")
            return {
                'country': 'United States',
                'name': f'{symbol} Inc.',
                'address': '123 Main Street New York NY',
                'zip_code': '10001',
                'nature': 'Public Limited Company'
            }
    
    def _cache_company_info(self, symbol: str, info: Dict[str, str]):
        """Cache company information and save immediately"""
        if "stocks" not in self.public_data:
            self.public_data["stocks"] = {}
        if symbol not in self.public_data["stocks"]:
            self.public_data["stocks"][symbol] = {"prices": {}, "company_info": {}}
        
        self.public_data["stocks"][symbol]["company_info"] = info
        
        # Save to file immediately
        self._save_cache_silently()
    
    def validate_sales_and_get_remaining_shares(self, symbol: str, vest_date: str, original_shares: int, sell_data: dict) -> int:
        """Validate sales against vests and return remaining shares"""
        symbol_sales = sell_data.get(symbol, {}).get("sales", [])
        total_sold = 0
        
        for sale in symbol_sales:
            if sale.get("purchase_date") == vest_date:
                total_sold += sale.get("number_of_shares_sold", 0)
        
        if total_sold > original_shares:
            print(f"{Colors.RED}❌ ERROR: Total sold shares ({total_sold}) exceeds original shares ({original_shares}) for {symbol} {vest_date}{Colors.NC}")
            sys.exit(1)
        
        remaining_shares = original_shares - total_sold
        
        if total_sold > 0:
            print(f"{Colors.YELLOW}📊 Lot partially held: {symbol} {vest_date} ({total_sold} sold, {remaining_shares} remaining of {original_shares}){Colors.NC}")
        
        return remaining_shares
    
    def get_sale_proceeds_for_lot(self, symbol: str, vest_date: str) -> float:
        """Get total sale proceeds for a specific vest lot"""
        try:
            with open(self.sell_file, 'r') as f:
                sell_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0.0
        
        symbol_sales = sell_data.get(symbol, {}).get("sales", [])
        total_proceeds = 0.0
        
        for sale in symbol_sales:
            if sale.get("purchase_date") == vest_date:
                total_proceeds += sale.get("sell_price_inr", 0.0)
        
        return total_proceeds
    
    def get_sale_proceeds_for_lot_in_year(self, symbol: str, vest_date: str, target_year: int, sell_data: dict) -> float:
        """Get total sale proceeds for a specific vest lot, but only for sales in the target year"""
        symbol_sales = sell_data.get(symbol, {}).get("sales", [])
        total_proceeds = 0.0
        
        for sale in symbol_sales:
            if sale.get("purchase_date") == vest_date:
                sell_date = sale.get("sell_date", "")
                # Only include sales from the target year
                if sell_date.startswith(str(target_year)):
                    total_proceeds += sale.get("sell_price_inr", 0.0)
        
        return total_proceeds
    
    def calculate_peak_value_with_sales(self, symbol: str, vest_date: str, original_shares: int, peak_price: float, peak_date: str, exchange_rate: float, sell_data: dict) -> float:
        """Calculate peak value by finding the date with highest (price × shares_held × exchange_rate)"""
        from datetime import datetime, timedelta
        
        # Get all sales for this vest lot in the target year
        symbol_sales = sell_data.get(symbol, {}).get("sales", [])
        lot_sales = []
        
        for sale in symbol_sales:
            if sale.get("purchase_date") == vest_date:
                sell_date = sale.get("sell_date", "")
                # Only consider sales in the target year
                if sell_date.startswith(str(self.year)):
                    lot_sales.append({
                        "sell_date": sell_date,
                        "shares_sold": sale.get("number_of_shares_sold", 0)
                    })
        
        # Sort sales by date
        lot_sales.sort(key=lambda x: x["sell_date"])
        
        # Get the date range for peak calculation (from vest date to end of year)
        vest_dt = datetime.strptime(vest_date, "%Y-%m-%d")
        year_start = max(vest_dt, datetime(self.year, 1, 1))
        year_end = datetime(self.year, 12, 31)
        
        # Get all stock prices for the symbol in the year
        stock_data = self.public_data.get("stocks", {}).get(symbol, {})
        year_prices = {}
        
        # Collect all available prices in the year range
        for date_str, price in stock_data.get("prices", {}).items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if year_start <= date_obj <= year_end:
                    year_prices[date_str] = price
            except ValueError:
                continue
        
        if not year_prices:
            # Error out if daily prices are not available
            print(f"{Colors.RED}❌ ERROR: Daily price data not available for {symbol} in {self.year}. Cannot calculate accurate peak value.{Colors.NC}")
            return None
        
        # Find the date with maximum (price × shares_held) in USD first
        max_usd_value = 0.0
        best_date = None
        
        for date_str, price in year_prices.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Calculate shares held on this date
            shares_held = original_shares
            for sale in lot_sales:
                sale_date_obj = datetime.strptime(sale["sell_date"], "%Y-%m-%d")
                if sale_date_obj <= date_obj:
                    shares_held -= sale["shares_sold"]
            
            shares_held = max(0, shares_held)
            
            if shares_held > 0:
                # Calculate total USD value on this date (no exchange rate yet)
                usd_value = float(price) * shares_held
                
                if usd_value > max_usd_value:
                    max_usd_value = usd_value
                    best_date = date_str
        
        if best_date is None:
            print(f"{Colors.RED}❌ ERROR: No valid peak date found for {symbol} {vest_date}. All shares may have been sold.{Colors.NC}")
            return None
        
        # Now get the exchange rate for the peak date and convert to INR
        peak_date_exchange_rate = self.get_sbi_rate(best_date)
        if peak_date_exchange_rate is None:
            print(f"{Colors.RED}❌ ERROR: Exchange rate not available for peak date {best_date} for {symbol} {vest_date}.{Colors.NC}")
            return None
        
        # Final peak value in INR
        peak_value_inr = max_usd_value * peak_date_exchange_rate
        
        return peak_value_inr
    
    def get_peak_price_from_vest(self, symbol: str, vest_date: str) -> tuple:
        """Get peak price and date from vest date onwards within the tax year"""
        # Determine start and end dates for peak calculation
        vest_dt = datetime.strptime(vest_date, "%Y-%m-%d")
        year_start = datetime(self.year, 1, 1)
        year_end = datetime(self.year, 12, 31)
        
        start_date = max(vest_dt, year_start)
        end_date = year_end
        
        self.vprint(f"🔍 Calculating peak price for {symbol} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Check if we have comprehensive cached data (at least 80% of trading days)
        expected_days = self._count_trading_days(start_date, end_date)
        cached_days = self._count_cached_days(symbol, start_date, end_date)
        
        if cached_days < expected_days * 0.8:
            self.vprint(f"📊 Insufficient cached data ({cached_days}/{expected_days} days). Fetching day-by-day...")
            if self.no_internet:
                print(f"{Colors.RED}❌ ERROR: Insufficient cached data for peak calculation{Colors.NC}")
                print(f"{Colors.RED}   --no-internet mode enabled, cannot fetch missing data{Colors.NC}")
                print(f"{Colors.RED}   Please run without --no-internet to fetch missing data{Colors.NC}")
                return None, None
            self._fetch_year_data(symbol, start_date, end_date)
        
        # Calculate peak from cached data
        peak_price = 0.0
        peak_date = None
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Skip weekends
                date_str = current_date.strftime("%Y-%m-%d")
                price = self.get_stock_price(symbol, date_str)
                if price and price > peak_price:
                    peak_price = price
                    peak_date = date_str
            
            current_date += timedelta(days=1)
        
        self.vprint(f"📈 Peak price for {symbol}: ${peak_price:.2f} on {peak_date}")
        return peak_price, peak_date
    
    def _count_trading_days(self, start_date: datetime, end_date: datetime) -> int:
        """Count expected trading days between two dates"""
        count = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday=0, Friday=4
                count += 1
            current += timedelta(days=1)
        return count
    
    def _count_cached_days(self, symbol: str, start_date: datetime, end_date: datetime) -> int:
        """Count cached trading days for a symbol between two dates"""
        cached_prices = (self.public_data.get("stocks", {})
                        .get(symbol, {})
                        .get("prices", {}))
        
        count = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Skip weekends
                date_str = current.strftime("%Y-%m-%d")
                if date_str in cached_prices:
                    count += 1
            current += timedelta(days=1)
        return count
    
    def _count_missing_prices(self, symbol: str, start_date: datetime, end_date: datetime) -> int:
        """Count how many prices need to be fetched for the given period"""
        cached_prices = (self.public_data.get("stocks", {})
                        .get(symbol, {})
                        .get("prices", {}))
        
        count = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Skip weekends
                date_str = current.strftime("%Y-%m-%d")
                if date_str not in cached_prices:
                    count += 1
            current += timedelta(days=1)
        return count
    
    def _fetch_stock_price_silently(self, symbol: str, date: str) -> Optional[float]:
        """Fetch stock price without verbose messaging (for bulk operations)"""
        # Check if no-internet mode is enabled
        if self.no_internet:
            return None
        
        # Try multiple approaches for getting stock price
        for attempt in range(7):  # Try up to 7 days back for weekends/holidays
            temp_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=attempt)
            temp_date_str = temp_date.strftime("%Y-%m-%d")
            
            # Skip weekends
            if temp_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            price = self._fetch_yahoo_price(symbol, temp_date_str)
            if price is not None:
                formatted_price = round(price, 2)
                
                # Cache both the original date and the actual trading date
                if symbol not in self.public_data["stocks"]:
                    self.public_data["stocks"][symbol] = {"prices": {}}
                if "prices" not in self.public_data["stocks"][symbol]:
                    self.public_data["stocks"][symbol]["prices"] = {}
                
                self.public_data["stocks"][symbol]["prices"][date] = formatted_price
                if temp_date_str != date:
                    self.public_data["stocks"][symbol]["prices"][temp_date_str] = formatted_price
                
                # Add to batch for incremental updates
                self.fetched_data['stock_prices'].append({
                    'symbol': symbol,
                    'date': date,
                    'price': formatted_price
                })
                if temp_date_str != date:
                    self.fetched_data['stock_prices'].append({
                        'symbol': symbol,
                        'date': temp_date_str,
                        'price': formatted_price
                    })
                
                return formatted_price
        
        return None
    
    def _fetch_single_day_price(self, symbol: str, date: str) -> Optional[float]:
        """Fetch stock price for a single day using JSON API"""
        try:
            # Convert date to timestamp
            dt = datetime.strptime(date, "%Y-%m-%d")
            timestamp = int(dt.timestamp())
            end_timestamp = timestamp + 86400
            
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            
            # Try multiple Yahoo Finance JSON endpoints
            endpoints = [
                f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={timestamp}&period2={end_timestamp}&interval=1d",
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={timestamp}&period2={end_timestamp}&interval=1d"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    
                    if response.status_code == 404:
                        continue  # Try next endpoint
                    elif response.status_code == 429:
                        print(f"⚠️  Rate limited, skipping this request...")
                        return None  # Skip instead of waiting
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check if we have valid data
                        if not data.get('chart') or not data['chart'].get('result'):
                            continue
                        
                        result = data['chart']['result'][0]
                        
                        # Get timestamps to match exact date
                        timestamps = result.get('timestamp', [])
                        target_date = date  # YYYY-MM-DD format
                        
                        # Extract close price
                        if 'indicators' in result and result['indicators'].get('quote'):
                            quotes = result['indicators']['quote'][0]
                            if 'close' in quotes and quotes['close']:
                                close_prices = quotes['close']
                                # Find close price that matches the exact date
                                for i in range(len(timestamps)):
                                    api_date = datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
                                    if api_date == target_date and i < len(close_prices) and close_prices[i] is not None:
                                        return round(float(close_prices[i]), 2)
                        
                        # Try alternative data structure
                        if 'meta' in result and 'regularMarketPrice' in result['meta']:
                            return round(float(result['meta']['regularMarketPrice']), 2)
                        
                except requests.RequestException as e:
                    if hasattr(e, 'response') and e.response:
                        status_code = e.response.status_code
                        if status_code != 404:  # Don't print 404 errors
                            print(f"⚠️  API error for {symbol}: {status_code}")
                    continue
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        except Exception as e:
            print(f"⚠️  Error fetching {symbol} price for {date}: {e}")
        
        return None
    
    def _fetch_year_data(self, symbol: str, start_date: datetime, end_date: datetime) -> bool:
        """Fetch daily stock prices for the entire period day by day"""
        self.vprint(f"📅 Fetching {symbol} data day by day...")
        
        # Check if no-internet mode is enabled
        if self.no_internet:
            return False
        
        current_date = start_date
        fetch_count = 0
        total_cached = 0
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Skip weekends
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Check if already cached
                cached_price = (self.public_data.get("stocks", {})
                               .get(symbol, {})
                               .get("prices", {})
                               .get(date_str))
                
                if cached_price is None:
                    # Show progress every 10 fetches
                    if fetch_count % 10 == 0:
                        missing_total = self._count_missing_prices(symbol, start_date, end_date)
                        self.vprint(f"📅 {symbol}: Fetching prices... ({fetch_count + 1}/{missing_total})")
                    
                    # Fetch single day price using JSON API
                    price = self._fetch_single_day_price(symbol, date_str)
                    
                    if price is not None:
                        # Cache the price immediately
                        if symbol not in self.public_data["stocks"]:
                            self.public_data["stocks"][symbol] = {"prices": {}}
                        if "prices" not in self.public_data["stocks"][symbol]:
                            self.public_data["stocks"][symbol]["prices"] = {}
                        
                        self.public_data["stocks"][symbol]["prices"][date_str] = price
                        total_cached += 1
                        
                        # Save to file immediately (silent update)
                        self._save_cache_silently()
                    
                    fetch_count += 1
                    
                    # 1 second delay between requests (faster like shell script)
                    time.sleep(1)
            
            current_date += timedelta(days=1)
        
        if total_cached > 0:
            return True
        else:
            return False
    
    
    def _fetch_yahoo_week_data(self, symbol: str, start_date: datetime, end_date: datetime) -> dict:
        """Fetch one week of stock prices in one API call"""
        try:
            # Convert dates to timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://finance.yahoo.com/',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Try multiple Yahoo Finance endpoints for week data
            endpoints = [
                f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d",
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"
            ]
            
            for endpoint in endpoints:
                try:
                    # Delay to avoid rate limiting
                    time.sleep(0.5)
                    response = requests.get(endpoint, headers=headers, timeout=30)
                    
                    if response.status_code == 404:
                        continue  # Try next endpoint
                    elif response.status_code == 429:
                        print(f"⚠️  Rate limited for {symbol}, waiting 5 seconds...")
                        time.sleep(5)
                        # Retry once more
                        response = requests.get(endpoint, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check if we have valid data
                        if not data.get('chart') or not data['chart'].get('result'):
                            continue
                        
                        result = data['chart']['result'][0]
                        
                        # Extract timestamps and close prices
                        if 'timestamp' in result and 'indicators' in result:
                            timestamps = result['timestamp']
                            quotes = result['indicators'].get('quote', [])
                            
                            if quotes and 'close' in quotes[0]:
                                close_prices = quotes[0]['close']
                                
                                # Build date -> price mapping
                                price_data = {}
                                for i, timestamp in enumerate(timestamps):
                                    if i < len(close_prices) and close_prices[i] is not None:
                                        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                                        price_data[date_str] = round(float(close_prices[i]), 2)
                                
                                return price_data
                        
                except requests.RequestException as e:
                    if hasattr(e, 'response') and e.response:
                        status_code = e.response.status_code
                        if status_code == 429:
                            print(f"⚠️  Rate limited for {symbol}, waiting 5 seconds...")
                            time.sleep(5)
                        elif status_code != 404:
                            print(f"⚠️  API error for {symbol}: {status_code}")
                    continue
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    continue
        
        except Exception as e:
            print(f"⚠️  Unexpected error fetching {symbol} week data: {e}")
        
        return {}
    
    def _save_cache_silently(self):
        """Save cache to file without any messages"""
        try:
            self.save_public_data()
        except Exception:
            pass  # Silent failure, don't interrupt the main process
    
    def update_incremental_cache(self):
        """Update cache incrementally with fetched stock prices"""
        if not self.fetched_data['stock_prices']:
            return
        
        # Silent update - no message
        
        # Save to file
        self.save_public_data()
        
        # Clear the batch
        self.fetched_data['stock_prices'] = []
    
    def _filter_zero_shares(self, data: Dict, data_type: str) -> Dict:
        """Filter out entries with 0 shares and print warnings"""
        filtered_data = {}
        
        for symbol, symbol_data in data.items():
            filtered_symbol_data = {"vests": [], "sales": []}
            
            if data_type == "vest":
                # Filter vests with 0 shares
                for vest in symbol_data.get("vests", []):
                    shares = vest.get("number_of_shares", 0)
                    if shares == 0:
                        print(f"{Colors.RED}⚠️  Warning: Ignoring {symbol} vest on {vest.get('vest_date', 'unknown date')} - 0 shares{Colors.NC}")
                    else:
                        filtered_symbol_data["vests"].append(vest)
            
            elif data_type == "sell":
                # Filter sales with 0 shares
                for sale in symbol_data.get("sales", []):
                    shares = sale.get("number_of_shares_sold", 0)
                    if shares == 0:
                        print(f"{Colors.RED}⚠️  Warning: Ignoring {symbol} sale on {sale.get('sell_date', 'unknown date')} - 0 shares{Colors.NC}")
                    else:
                        filtered_symbol_data["sales"].append(sale)
            
            # Only include symbol if it has non-zero entries
            if filtered_symbol_data["vests"] or filtered_symbol_data["sales"]:
                filtered_data[symbol] = filtered_symbol_data
        
        return filtered_data
    
    def validate_and_prepare_data(self):
        """Validate input data and prepare required data fetching"""
        self.print_always(f"{Colors.GREEN}🔍 Step 1: Validating input data...{Colors.NC}")
        
        # Load vest data
        try:
            with open(self.vest_file, 'r') as f:
                vest_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"{Colors.RED}❌ Error reading {self.vest_file}: {e}{Colors.NC}")
            return None
        
        # Load sell data
        try:
            with open(self.sell_file, 'r') as f:
                sell_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"{Colors.RED}❌ Error reading {self.sell_file}: {e}{Colors.NC}")
            return None
        
        self.vprint("✓ Input files loaded successfully")
        
        # Filter out entries with 0 shares and print warnings
        vest_data = self._filter_zero_shares(vest_data, "vest")
        sell_data = self._filter_zero_shares(sell_data, "sell")
        
        self.vprint("🔍 Validating sales against vest lots...")
        
        # Validate all sales against vests
        all_valid = True
        for symbol, symbol_data in sell_data.items():
            for sale in symbol_data.get("sales", []):
                vest_date = sale["purchase_date"]
                sell_date = sale["sell_date"]
                shares_sold = sale["number_of_shares_sold"]
                
                # Validate that sell date is after vest date
                if sell_date <= vest_date:
                    print(f"{Colors.RED}❌ Invalid sale: {symbol} {vest_date} - sell date ({sell_date}) must be after vest date{Colors.NC}")
                    all_valid = False
                
                # Find matching vest
                vest_found = False
                if symbol in vest_data:
                    for vest in vest_data[symbol].get("vests", []):
                        if vest["vest_date"] == vest_date:
                            if vest["number_of_shares"] < shares_sold:
                                print(f"{Colors.RED}❌ Invalid sale: {symbol} {vest_date} - trying to sell {shares_sold} shares but only {vest['number_of_shares']} available{Colors.NC}")
                                all_valid = False
                            vest_found = True
                            break
                
                if not vest_found:
                    print(f"{Colors.RED}❌ Invalid sale: {symbol} {vest_date} - no matching vest found{Colors.NC}")
                    all_valid = False
        
        if not all_valid:
            return None
        
        self.vprint("✓ All sales validated successfully")
        return vest_data, sell_data
    
    def validate_vest_prices(self, vest_data: dict) -> bool:
        """Validate all vest prices against day's high-low ranges"""
        has_vest_prices = False
        
        for symbol, symbol_data in vest_data.items():
            for vest in symbol_data.get("vests", []):
                vest_price = vest.get("vest_price_optional")
                
                if vest_price is not None:
                    has_vest_prices = True
                    vest_date = vest["vest_date"]
                    
                    self.vprint(f"🎯 Validating vest price for {symbol} {vest_date}: ${vest_price}")
                    
                    # Get day's high-low range for validation
                    day_high_low = self.get_day_high_low_prices(symbol, vest_date)
                    
                    if day_high_low:
                        day_low, day_high = day_high_low
                        if day_low <= vest_price <= day_high:
                            self.vprint(f"✅ Vest price ${vest_price} is valid (within range ${day_low}-${day_high})")
                        else:
                            print(f"{Colors.RED}❌ ERROR: Vest price ${vest_price} is outside valid range ${day_low}-${day_high} for {symbol} on {vest_date}{Colors.NC}")
                            print(f"{Colors.RED}   Please verify the vest price is correct and try again{Colors.NC}")
                            return False
                    else:
                        print(f"{Colors.YELLOW}⚠️  Could not validate vest price - no high/low data available for {symbol} on {vest_date}{Colors.NC}")
                        self.vprint(f"🎯 Vest price ${vest_price} will be used without validation")
        
        if has_vest_prices:
            self.vprint("✅ All vest prices validated successfully")
        else:
            print("ℹ️  No vest prices provided - will use market data")
        
        return True
    
    def fetch_required_data(self, vest_data, sell_data):
        """Fetch all required data from internet and update cache"""
        self.print_always(f"{Colors.GREEN}🌐 Step 2: Fetching required data from internet...{Colors.NC}")
        
        # Collect all required dates and symbols
        required_symbols = set()
        required_dates = set()
        symbol_specific_dates = {}  # Track which dates are needed for each symbol
        
        for symbol, symbol_data in vest_data.items():
            required_symbols.add(symbol)
            symbol_dates = set()
            
            # Add vest dates
            for vest in symbol_data.get("vests", []):
                vest_date = vest["vest_date"]
                required_dates.add(vest_date)
                symbol_dates.add(vest_date)
            
            # Add calculation year dates (Jan 1, Dec 31)
            jan1_date = f"{self.year}-01-01"
            dec31_date = f"{self.year}-12-31"
            required_dates.add(jan1_date)
            required_dates.add(dec31_date)
            symbol_dates.add(jan1_date)
            symbol_dates.add(dec31_date)
            
            # Add sell dates for this symbol
            symbol_sales = sell_data.get(symbol, {}).get("sales", [])
            for sale in symbol_sales:
                sell_date = sale.get("sell_date")
                if sell_date:
                    required_dates.add(sell_date)
                    symbol_dates.add(sell_date)
            
            symbol_specific_dates[symbol] = symbol_dates
        
        # Fetch calculation year data for peak calculation (efficient bulk fetch)
        for symbol in required_symbols:
            start_date = datetime(self.year, 1, 1)
            end_date = datetime(self.year, 12, 31)
            
            self.vprint(f"📊 Preparing to fetch {symbol} data for peak calculation ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
            missing_count = self._count_missing_prices(symbol, start_date, end_date)
            if missing_count > 0:
                self.vprint(f"🌐 Need to fetch {missing_count} missing prices for {symbol}")
                success = self._fetch_year_data(symbol, start_date, end_date)
                if not success and not self.no_internet:
                    print(f"⚠️  Failed to fetch {symbol} data for peak calculation")
            else:
                self.vprint(f"✓ {symbol} data already cached")
        
        # Fetch specific required dates that are not in the calculation year
        self.vprint("📅 Fetching specific required dates...")
        for symbol, dates in symbol_specific_dates.items():
            missing_dates = []
            for date in dates:
                # Check if date is already cached
                cached_price = (self.public_data.get("stocks", {})
                               .get(symbol, {})
                               .get("prices", {})
                               .get(date))
                if cached_price is None:
                    missing_dates.append(date)
            
            if missing_dates:
                self.vprint(f"🌐 Fetching {len(missing_dates)} missing dates for {symbol}: {missing_dates}")
                
                # Group dates by proximity and fetch in small ranges
                for date in missing_dates:
                    if self.no_internet:
                        print(f"{Colors.RED}❌ ERROR: Missing price for {symbol} on {date}{Colors.NC}")
                        print(f"{Colors.RED}   --no-internet mode enabled, cannot fetch from internet{Colors.NC}")
                        return False
                    
                    # Use the efficient _fetch_yahoo_price method (which now uses bulk fetch)
                    price = self._fetch_yahoo_price(symbol, date)
                    if price is not None:
                        # Cache the price
                        if symbol not in self.public_data["stocks"]:
                            self.public_data["stocks"][symbol] = {"prices": {}}
                        if "prices" not in self.public_data["stocks"][symbol]:
                            self.public_data["stocks"][symbol]["prices"] = {}
                        
                        self.public_data["stocks"][symbol]["prices"][date] = round(price, 2)
                        self._save_cache_silently()
                        print(f"✅ Cached {symbol} price for {date}: ${price}")
                    else:
                        print(f"❌ Failed to fetch {symbol} price for {date}")
                        return False
        
        # Fetch company info for all symbols
        self.vprint("📋 Fetching company information...")
        for symbol in required_symbols:
            company_info = self.get_company_info(symbol)
            if company_info is None and self.no_internet:
                return False
        
        # Fetch exchange rates for all required dates
        self.vprint("💱 Fetching exchange rates...")
        exchange_rates_fetched = 0
        initial_exchange_count = len(self.public_data.get("exchange_rates", {}))
        
        for date in required_dates:
            sbi_rate = self.get_sbi_rate(date)
            if sbi_rate is None and self.no_internet:
                return False
        
        # Check how many exchange rates were actually fetched
        final_exchange_count = len(self.public_data.get("exchange_rates", {}))
        exchange_rates_fetched = final_exchange_count - initial_exchange_count
        
        if exchange_rates_fetched > 0:
            self.vprint(f"✓ Cached {exchange_rates_fetched} exchange rates")
        
        # Fetch high/low prices for vest dates (needed for vest price validation)
        if not self.exclude_validation:
            self.vprint("📊 Fetching high/low prices for vest dates...")
            self.fetch_high_low_prices_for_vests(vest_data)
        else:
            self.vprint("⏭️  Skipping high/low price fetching (validation excluded)")
        
        self.vprint("✓ All required data fetched and cached")
        return True
    
    def sort_all_json_files(self):
        """Sort all JSON files: vest.json, sell.json, and public_data.json"""
        self.vprint("📋 Sorting vest.json...")
        self._sort_vest_json()
        
        self.vprint("📋 Sorting sell.json...")
        self._sort_sell_json()
        
        self.vprint("📋 Sorting public_data.json...")
        self.save_public_data()  # This already sorts public_data.json
        
        self.vprint("✅ All JSON files sorted successfully")
    
    def _sort_vest_json(self):
        """Sort vest.json by stock symbols and vest dates"""
        try:
            with open(self.vest_file, 'r') as f:
                vest_data = json.load(f)
            
            # Sort by stock symbols (keys)
            sorted_vest_data = {}
            for symbol in sorted(vest_data.keys()):
                symbol_data = vest_data[symbol]
                
                # Sort vests by date
                if 'vests' in symbol_data:
                    sorted_vests = sorted(
                        symbol_data['vests'], 
                        key=lambda x: x['vest_date']
                    )
                    sorted_vest_data[symbol] = {'vests': sorted_vests}
                else:
                    sorted_vest_data[symbol] = symbol_data
            
            # Write sorted data back to file
            with open(self.vest_file, 'w') as f:
                json.dump(sorted_vest_data, f, indent=2)
                
        except Exception as e:
            self.vprint(f"⚠️  Could not sort vest.json: {e}")
    
    def _sort_sell_json(self):
        """Sort sell.json by stock symbols and sell dates"""
        try:
            if not self.sell_file.exists():
                return  # No sell file to sort
                
            with open(self.sell_file, 'r') as f:
                sell_data = json.load(f)
            
            # Sort by stock symbols (keys)
            sorted_sell_data = {}
            for symbol in sorted(sell_data.keys()):
                symbol_data = sell_data[symbol]
                
                # Sort sales by date
                if 'sales' in symbol_data:
                    sorted_sales = sorted(
                        symbol_data['sales'], 
                        key=lambda x: x['sell_date']
                    )
                    sorted_sell_data[symbol] = {'sales': sorted_sales}
                else:
                    sorted_sell_data[symbol] = symbol_data
            
            # Write sorted data back to file
            with open(self.sell_file, 'w') as f:
                json.dump(sorted_sell_data, f, indent=2)
                
        except Exception as e:
            self.vprint(f"⚠️  Could not sort sell.json: {e}")
    
    def fetch_high_low_prices_for_vests(self, vest_data: dict):
        """Fetch high/low prices for all vest dates that have vest_price"""
        for symbol, symbol_data in vest_data.items():
            for vest in symbol_data.get("vests", []):
                if vest.get("vest_price_optional") is not None:
                    vest_date = vest["vest_date"]
                    self.vprint(f"📊 Fetching high/low for {symbol} {vest_date}")
                    
                    # Fetch and cache high/low data
                    high_low = self._fetch_day_high_low_from_api(symbol, vest_date)
                    if high_low:
                        self._cache_high_low_prices(symbol, vest_date, high_low[0], high_low[1])
    
    def get_day_high_low_prices(self, symbol: str, date: str) -> Optional[tuple]:
        """Get day's high and low prices for a symbol on a specific date"""
        # Check cache first
        cached_high_low = (self.public_data.get("stocks", {})
                          .get(symbol, {})
                          .get("high_low", {})
                          .get(date))
        
        if cached_high_low:
            return (cached_high_low["low"], cached_high_low["high"])
        
        # If not cached and internet is disabled, return None
        if self.no_internet:
            return None
        
        # Fetch from internet
        high_low = self._fetch_day_high_low_from_api(symbol, date)
        if high_low:
            self._cache_high_low_prices(symbol, date, high_low[0], high_low[1])
            return high_low
        
        return None
    
    def _fetch_day_high_low_from_api(self, symbol: str, date: str) -> Optional[tuple]:
        """Fetch day's high and low prices from Yahoo Finance API"""
        try:
            # Convert date to timestamp
            dt = datetime.strptime(date, "%Y-%m-%d")
            timestamp = int(dt.timestamp())
            end_timestamp = timestamp + 86400
            
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            
            # Use Yahoo Finance API
            endpoint = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={timestamp}&period2={end_timestamp}&interval=1d"
            
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data.get('chart') or not data['chart'].get('result'):
                return None
            
            result = data['chart']['result'][0]
            
            # Get timestamps to match exact date
            timestamps = result.get('timestamp', [])
            target_date = date  # YYYY-MM-DD format
            
            # Extract high and low prices
            if 'indicators' in result and result['indicators'].get('quote'):
                quote = result['indicators']['quote'][0]
                if 'high' in quote and 'low' in quote:
                    highs = quote['high']
                    lows = quote['low']
                    
                    # Find data point that matches the exact date
                    for i in range(len(timestamps)):
                        api_date = datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
                        if api_date == target_date and highs[i] is not None and lows[i] is not None:
                            return (float(lows[i]), float(highs[i]))
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error fetching high/low for {symbol} on {date}: {e}")
            return None
    
    def _cache_high_low_prices(self, symbol: str, date: str, low: float, high: float):
        """Cache high/low prices for a symbol and date"""
        if "stocks" not in self.public_data:
            self.public_data["stocks"] = {}
        if symbol not in self.public_data["stocks"]:
            self.public_data["stocks"][symbol] = {}
        if "high_low" not in self.public_data["stocks"][symbol]:
            self.public_data["stocks"][symbol]["high_low"] = {}
        
        self.public_data["stocks"][symbol]["high_low"][date] = {
            "low": round(low, 2),
            "high": round(high, 2)
        }
        
        self._save_cache_silently()
    
    def process_fa_calculations(self):
        """Main processing function for FA calculations"""
        print(f"{Colors.GREEN}Processing Foreign Assets Schedule for year {self.year}{Colors.NC}")
        
        # Step 1: Validate input data
        validation_result = self.validate_and_prepare_data()
        if validation_result is None:
            return False
        vest_data, sell_data = validation_result
        
        # Step 2: Fetch required data
        if not self.fetch_required_data(vest_data, sell_data):
            return False
        
        # Step 2.5: Validate vest prices (now that we have high/low data)
        if not self.exclude_validation:
            self.vprint("🔍 Validating vest prices...")
            if not self.validate_vest_prices(vest_data):
                return False
        else:
            self.vprint("⏭️  Skipping vest price validation (-x flag enabled)")
        
        # Step 3: Sort all JSON files
        if not self.no_sort:
            self.print_always(f"{Colors.GREEN}📋 Step 3: Sorting data files...{Colors.NC}")
            self.sort_all_json_files()
        else:
            self.print_always(f"{Colors.GREEN}📋 Step 3: Skipping data file sorting (-y flag enabled){Colors.NC}")
        
        self.print_always(f"{Colors.GREEN}🧮 Step 4: Calculating Foreign Assets Schedule...{Colors.NC}")
        
        # Prepare CSV data
        csv_rows = []
        
        # Process each stock and vest
        for symbol, symbol_data in vest_data.items():
            for vest in symbol_data.get("vests", []):
                vest_date = vest["vest_date"]
                original_shares = vest["number_of_shares"]
                
                self.vprint(f"Processing vest: {symbol} {vest_date}, {original_shares} shares")
                
                # Validate sales and get remaining shares
                remaining_shares = self.validate_sales_and_get_remaining_shares(
                    symbol, vest_date, original_shares, sell_data)
                
                if remaining_shares == 0:
                    print(f"{Colors.YELLOW}⏭️  Skipping fully sold lot: {symbol} {vest_date}{Colors.NC}")
                    print("---")
                    continue
                
                self.vprint(f"{Colors.GREEN}📊 Processing FA calculation for {remaining_shares} remaining shares{Colors.NC}")
                
                # Get stock prices (should be cached now)
                vest_price = self.get_purchase_price_with_vest_override(symbol, vest_date, vest)
                jan1_price = self.get_stock_price(symbol, f"{self.year}-01-01")
                dec31_price = self.get_stock_price(symbol, f"{self.year}-12-31")
                peak_price, peak_date = self.get_peak_price_from_vest(symbol, vest_date)
                
                # Get SBI exchange rates (should be cached now)
                vest_sbi_rate = self.get_sbi_rate(vest_date)
                dec31_sbi_rate = self.get_sbi_rate(f"{self.year}-12-31")
                
                # Check if any required data is missing
                if None in [vest_price, jan1_price, dec31_price, peak_price, vest_sbi_rate, dec31_sbi_rate]:
                    print(f"{Colors.RED}❌ ERROR: Missing critical data for {symbol} {vest_date}{Colors.NC}")
                    if vest_price is None:
                        print(f"{Colors.RED}   - Purchase price for {vest_date} could not be fetched{Colors.NC}")
                    if jan1_price is None:
                        print(f"{Colors.RED}   - Jan 1 price for {self.year} could not be fetched{Colors.NC}")
                    if dec31_price is None:
                        print(f"{Colors.RED}   - Dec 31 price for {self.year} could not be fetched{Colors.NC}")
                    if peak_price is None:
                        print(f"{Colors.RED}   - Peak price could not be calculated{Colors.NC}")
                    if vest_sbi_rate is None:
                        print(f"{Colors.RED}   - SBI exchange rate for {vest_date} could not be fetched{Colors.NC}")
                    if dec31_sbi_rate is None:
                        print(f"{Colors.RED}   - SBI exchange rate for {self.year}-12-31 could not be fetched{Colors.NC}")
                    print(f"{Colors.RED}   Cannot proceed with accurate calculations. Exiting.{Colors.NC}")
                    return False
                
                self.vprint(f"Prices: Purchase=${vest_price}, Jan1=${jan1_price}, Dec31=${dec31_price}, Peak=${peak_price} on {peak_date}")
                self.vprint(f"SBI Rates: Purchase=₹{vest_sbi_rate}, Dec31=₹{dec31_sbi_rate}")
                
                # Calculate values in INR
                # Always use vest price and vest date exchange rate for initial value
                initial_value = vest_price * remaining_shares * vest_sbi_rate
                
                # Calculate other values
                peak_value = self.calculate_peak_value_with_sales(symbol, vest_date, original_shares, peak_price, peak_date, dec31_sbi_rate, sell_data)
                if peak_value is None:
                    print(f"{Colors.RED}❌ ERROR: Could not calculate peak value for {symbol} {vest_date}. Skipping this lot.{Colors.NC}")
                    continue
                
                closing_balance = dec31_price * remaining_shares * dec31_sbi_rate
                
                # Gross amount paid: Always set to 0
                gross_amount_paid = 0.0
                
                # Gross proceeds: Only if sold in target year, otherwise 0
                gross_proceeds = self.get_sale_proceeds_for_lot_in_year(symbol, vest_date, self.year, sell_data)
                
                # Get company information
                company_info = self.get_company_info(symbol)
                
                # Get country code from country mapping
                country_name = company_info['country']
                country_mapping = self.public_data.get("country_mapping", {})
                country_code = country_mapping.get(country_name, 2)  # Default to 2 (United States) if not found
                
                # Create CSV row
                csv_row = [
                    symbol,
                    vest_date,
                    company_info['country'],
                    company_info['name'],
                    company_info['address'],
                    company_info['zip_code'],
                    company_info['nature'],
                    vest_date,  # Date of acquiring interest
                    int(round(initial_value)),
                    int(round(peak_value)),
                    int(round(closing_balance)),
                    int(round(gross_amount_paid)),
                    int(round(gross_proceeds))
                ]
                
                csv_rows.append(csv_row)
                
                self.print_always(f"{Colors.YELLOW}Processed: {symbol} {vest_date} lot{Colors.NC}")
                self.vprint(f"Shares: {remaining_shares} remaining (of {original_shares} original)")
                self.vprint(f"Initial: ₹{initial_value:.2f}, Peak: ₹{peak_value:.2f}, Closing: ₹{closing_balance:.2f}")
                self.vprint(f"Paid: ₹{gross_amount_paid:.2f}, Proceeds: ₹{gross_proceeds:.2f}")
                self.vprint("---")
        
        # Sort CSV rows by stock symbol and then by date
        csv_rows.sort(key=lambda x: (x[0], x[1]))
        
        # Write to FA.csv
        self.write_fa_csv(csv_rows)
        
        # Update cache with any remaining fetched data
        self.update_final_cache()
        
        return True
    
    def write_fa_csv(self, csv_rows: List[List[str]]):
        """Write FA calculation results to CSV file"""
        # CSV header
        header = [
            "Country/Region name", "Country Name and Code", "Name of entity", "Address of entity", "ZIP Code",
            "Nature of entity", "Date of acquiring the interest", "Initial value of the investment",
            "Peak value of investment during the Period", "Closing balance",
            "Total gross amount paid/credited with respect to the holding during the period", "Total gross proceeds from sale or redemption of investment during the period"
        ]
        
        # Clear existing FA.csv and write new data
        with open(self.fa_csv, 'w', newline='') as f:
            # Write header with quotes manually
            quoted_header_line = ','.join([f'"{col}"' for col in header])
            f.write(quoted_header_line + '\n')
            
            # Write data rows without quotes
            writer = csv.writer(f, quoting=csv.QUOTE_NONE)
            for i, row in enumerate(csv_rows, 1):
                # First column: serial number, Second column: country code from mapping
                # row[2:] = [country, name, address, zip, nature, date, initial, peak, closing, paid, proceeds]
                country_name = row[2]
                country_mapping = self.public_data.get("country_mapping", {})
                country_code = country_mapping.get(country_name, 2)  # Default to 2 (United States) if not found
                data_row = [i, country_code] + row[3:]  # Serial number, country code from mapping, then name, address, etc.
                writer.writerow(data_row)
        
        print(f"{Colors.GREEN}✅ FA calculations completed! Results written to {self.fa_csv}{Colors.NC}")
        print(f"{Colors.GREEN}📊 Total rows processed: {len(csv_rows)}{Colors.NC}")
    
    def update_final_cache(self):
        """Update cache with any remaining fetched data"""
        total_updates = (len(self.fetched_data['stock_prices']) + 
                        len(self.fetched_data['exchange_rates']))
        
        if total_updates > 0:
            print(f"{Colors.GREEN}💾 Updating cache with {total_updates} new entries...{Colors.NC}")
            self.save_public_data()
            print(f"{Colors.GREEN}✅ Cache updated successfully!{Colors.NC}")


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        """Override error method to provide better error messages"""
        if 'required' in message and 'year' in message:
            print(f"{Colors.RED}❌ Error: Tax {Colors.YELLOW}year{Colors.RED} argument is required{Colors.NC}")
            print(f"{Colors.YELLOW}💡 Usage: python3 fa_calculator.py {Colors.YELLOW}<year>{Colors.NC}")
            print(f"{Colors.YELLOW}   Example: python3 fa_calculator.py {Colors.YELLOW}2023{Colors.NC}")
            print(f"{Colors.BLUE}ℹ️  Use --help for more options{Colors.NC}")
        else:
            print(f"{Colors.RED}❌ Error: {message}{Colors.NC}")
            print(f"{Colors.BLUE}ℹ️  Use --help for usage information{Colors.NC}")
        sys.exit(2)

def main():
    # Custom help formatter to add yellow color to arguments
    class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def _format_action_invocation(self, action):
            if not action.option_strings:
                # Positional argument
                metavar, = self._metavar_formatter(action, action.dest)(1)
                return f'{Colors.YELLOW}{metavar}{Colors.NC}'
            else:
                # Optional argument
                parts = []
                if action.nargs == 0:
                    parts.extend([f'{Colors.YELLOW}{option_string}{Colors.NC}' for option_string in action.option_strings])
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        parts.append(f'{Colors.YELLOW}{option_string}{Colors.NC}')
                    if args_string:
                        parts[-1] += f' {Colors.YELLOW}{args_string}{Colors.NC}'
                return ', '.join(parts)
    
    parser = CustomArgumentParser(
        description=f"{Colors.GREEN}Foreign Assets Schedule Calculator for ITR (for foreign stocks related section A3 only){Colors.NC}",
        formatter_class=ColoredHelpFormatter,
        epilog=f"""
Examples:
  python3 fa_calculator.py {Colors.YELLOW}2024{Colors.NC}                    # Calculate FA for 2024, fetch missing data
  python3 fa_calculator.py {Colors.YELLOW}--no-internet{Colors.NC} {Colors.YELLOW}2024{Colors.NC}     # Calculate FA for 2024, cache-only mode
  python3 fa_calculator.py {Colors.YELLOW}--data{Colors.NC} ./data {Colors.YELLOW}2024{Colors.NC}        # Use custom data directory
        """
    )
    
    parser.add_argument('year', type=int, help=f'Tax year for calculation (e.g., {Colors.YELLOW}2024{Colors.NC})')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output with detailed progress information')
    parser.add_argument('-x', '--exclude-validation', action='store_true', 
                       help='Exclude vest price validation (skip vest price checks)')
    parser.add_argument('-y', '--no-sort', action='store_true', 
                       help='Skip sorting of input JSON files')
    parser.add_argument('--no-internet', action='store_true', 
                       help='Only use cached data, exit with error if data missing')
    parser.add_argument('--data', default=None,
                       help=f'Data directory containing vest.json, sell.json, public_data.json (default: {Colors.YELLOW}script directory{Colors.NC})')
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit(), we catch it to handle it gracefully
        sys.exit(e.code)
    
    # Create calculator instance
    calculator = FACalculator(
        year=args.year,
        no_internet=args.no_internet,
        data_dir=args.data,
        verbose=args.verbose,
        exclude_validation=args.exclude_validation,
        no_sort=args.no_sort
    )
    
    # Validate year
    if not calculator.validate_year():
        sys.exit(1)
    
    # Check if data directory exists
    if not calculator.data_dir.exists():
        print(f"{Colors.RED}❌ Error: Data directory '{calculator.data_dir}' not found{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Please create the data directory or specify a valid path with --data{Colors.NC}")
        sys.exit(1)
    
    # Check if required files exist
    if not calculator.vest_file.exists():
        print(f"{Colors.RED}❌ Error: Vest file '{calculator.vest_file}' not found{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Please ensure vest.json exists in the data directory{Colors.NC}")
        print(f"{Colors.BLUE}ℹ️  This file should contain your stock vest transactions{Colors.NC}")
        sys.exit(1)
    
    if not calculator.sell_file.exists():
        print(f"{Colors.RED}❌ Error: Sell file '{calculator.sell_file}' not found{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Please ensure sell.json exists in the data directory{Colors.NC}")
        print(f"{Colors.BLUE}ℹ️  This file should contain your stock sale transactions{Colors.NC}")
        sys.exit(1)
    
    # Process FA calculations
    success = calculator.process_fa_calculations()
    
    if not success:
        print(f"{Colors.RED}❌ FA calculation failed{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.YELLOW}📝 Dividends are not handled currently. Add dividend manually in gross amount paid column (second last column).{Colors.NC}")
    
    print(f"\n{Colors.YELLOW}💡 Next steps:{Colors.NC}")
    print("  1. Review the generated FA.csv file")
    print("  2. Data fetched from internet was shown in RED")
    print("  3. Future runs will use cached data (shown in GREEN)")


if __name__ == "__main__":
    main()
    