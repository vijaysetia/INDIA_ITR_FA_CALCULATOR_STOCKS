# Core Tests for FA Calculator

This directory contains core functionality tests for the FA Calculator. These tests verify the correctness and completeness of FA.csv generation using pre-cached data (no internet required).

## 📂 Directory Structure

```
core-tests/
├── README.md                    # This file
├── run_core_tests.py           # Test runner script
├── data1/                      # Test case 1: Simple vest with no sales
│   ├── test_config.txt         # Test configuration (year, description)
│   ├── vest.json              # Input: vest transactions
│   ├── sell.json              # Input: sale transactions (empty)
│   ├── public_data.json       # Input: cached market data
│   └── expected_FA.csv        # Expected output for comparison
├── data2/                     # Test case 2: Vest with vest_price_optional
│   ├── test_config.txt
│   ├── vest.json
│   ├── sell.json
│   ├── public_data.json
│   └── expected_FA.csv
├── data3/                     # Test case 3: Vest with partial sales
│   ├── test_config.txt
│   ├── vest.json
│   ├── sell.json
│   ├── public_data.json
│   └── expected_FA.csv
├── data4/                     # Test case 4: Multiple vests and symbols
│   ├── test_config.txt
│   ├── vest.json
│   ├── sell.json
│   ├── public_data.json
│   └── expected_FA.csv
└── data5/                     # Test case 5: Peak after partial sale
    ├── test_config.txt
    ├── vest.json
    ├── sell.json
    ├── public_data.json
    └── expected_FA.csv
```

## 🧪 Test Cases

### data1 - Simple Vest (No Sales)
- **Description**: Basic vest with no sales transactions
- **Stock**: ACME Corp (100 shares vested on 2023-01-15)
- **Tests**: Basic calculation, peak value calculation, closing balance

### data2 - Vest Price Override
- **Description**: Vest with `vest_price_optional` field
- **Stock**: Beta Inc (50 shares vested on 2023-03-01 at $200.00)
- **Tests**: Custom vest price usage instead of market price

### data3 - Partial Sales
- **Description**: Vest with partial sales during the tax year
- **Stock**: Gamma Technologies (200 shares vested, 75 sold)
- **Tests**: Sale proceeds calculation, remaining shares calculation

### data4 - Multiple Vests
- **Description**: Multiple vests for same symbol and different symbols
- **Stocks**: Delta Systems (2 vests), Echo Dynamics (1 vest)
- **Tests**: Multiple lot processing, different symbols handling

### data5 - Peak After Sale (Advanced)
- **Description**: Peak stock value occurs AFTER partial sale
- **Stock**: Theta Systems (150 shares vested, 60 sold in June, peak in October)
- **Tests**: Complex peak calculation with changing share quantities, timing dependencies

## 🚀 Running Tests

### Run All Core Tests
```bash
cd tests/core-tests
python3 run_core_tests.py
```

### Run Single Test Manually
```bash
# From project root
python3 fa_calculator.py --data tests/core-tests/data1 2023 --no-internet -x -y
```

## 📊 Test Data Characteristics

### Stock Symbols
- **ACME**: Simple test stock
- **BETA**: Test stock with vest price override
- **GAMMA**: Test stock with sales
- **DELTA**: Test stock with multiple vests
- **ECHO**: Secondary test stock
- **THETA**: Test stock for peak-after-sale scenario

### Price Patterns
- All stocks have realistic price movements
- Peak prices occur at different times during the year
- Daily price data provided for accurate peak calculation

### Exchange Rates
- Realistic USD-INR rates for 2023
- Rates vary throughout the year (82.50 - 83.50)

### Company Information
- Dummy addresses and ZIP codes
- All companies are US-based (country code 2)
- Standard "Public Limited Company" nature

## ✅ Test Validation

The test runner compares generated `FA.csv` with `expected_FA.csv`:

1. **Header Validation**: Exact match required
2. **Data Validation**: Numerical tolerance of ±1 INR for rounding differences
3. **Line Count**: Must match exactly
4. **Column Count**: Must match exactly

## 🔧 Test Configuration

Each test directory contains `test_config.txt`:
```
year=2023
description=Test case description
```

## 📝 Adding New Tests

To add a new test case:

1. Create new directory: `data5/`
2. Add required files:
   - `test_config.txt`
   - `vest.json`
   - `sell.json` 
   - `public_data.json`
   - `expected_FA.csv`
3. Run tests to verify

## 🎯 Key Features Tested

- ✅ Basic vest processing
- ✅ Vest price overrides (`vest_price_optional`)
- ✅ Sales transaction processing
- ✅ Peak value calculation
- ✅ Multiple vests per symbol
- ✅ Multiple stock symbols
- ✅ Exchange rate application
- ✅ Company information handling
- ✅ CSV output formatting

## 🚨 Important Notes

- **No Internet Required**: All tests run with `--no-internet` flag
- **Cached Data**: All market data is pre-cached in `public_data.json`
- **Year 2023**: All tests use 2023 as the tax year
- **Dummy Data**: All company information and addresses are fictional
- **Simple Prices**: Stock prices are kept simple for easy verification

## 📈 Expected Test Results

When all tests pass, you should see:
```
🧪 Running Core Tests for FA Calculator
Found 4 test directories:
  Running data1 (year 2023)... PASSED
  Running data2 (year 2023)... PASSED
  Running data3 (year 2023)... PASSED
  Running data4 (year 2023)... PASSED

📊 TEST SUMMARY
Total tests: 4
Passed: 4
Failed: 0

🎉 All tests passed!
```
