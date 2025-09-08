# Data Fetching Tests for FA Calculator

This directory contains tests for the data fetching functionality of the FA Calculator. These tests validate internet connectivity, data retrieval, caching mechanisms, and data parsing while being respectful to external APIs through rate limiting and intelligent caching.

**🔍 Internet Connectivity Check**: The test suite automatically verifies internet connectivity at startup and exits with an error if no connection is available, preventing misleading test failures.

## 📂 Directory Structure

```
data-fetching-tests/
├── README.md                    # This file
├── run_data_fetching_tests.py  # Test runner script
└── test_data/                  # Auto-generated test data
    ├── vest.json              # Sample vest transactions for testing
    ├── sell.json              # Sample sale transactions (empty)
    └── public_data.json       # Cache that gets populated during tests
```

## 🌐 Test Cases

### Data Fetching & Caching
1. **stock_price_fetching** - Tests stock price retrieval and caching
2. **exchange_rate_fetching** - Tests USD-INR exchange rate fetching
3. **cache_persistence** - Tests that cached data persists between runs
4. **incremental_caching** - Tests adding new data without losing old cache

### Data Validation & Processing
5. **data_validation** - Tests that fetched data has correct structure and types
6. **vest_price_optional_override** - Tests that price overrides work correctly

### Offline & Error Handling
7. **no_internet_with_partial_cache** - Tests `--no-internet` with existing cache
8. **invalid_symbol_handling** - Tests graceful handling of invalid stock symbols
9. **rate_limiting_behavior** - Tests that API rate limiting is respected

## 🚀 Running Tests

### Run All Data Fetching Tests
```bash
cd tests/data-fetching-tests
python3 run_data_fetching_tests.py
```

### Expected Output
```
🌐 Running Data Fetching Tests for FA Calculator
Script: /path/to/fa_calculator.py
Test directory: /path/to/tests/data-fetching-tests
⚠️  These tests make real network calls - please be patient

  Running stock_price_fetching... PASSED
  Running exchange_rate_fetching... PASSED
  Running cache_persistence... PASSED
  Running vest_price_optional_override... PASSED
  Running no_internet_with_partial_cache... PASSED
  Running data_validation... PASSED
  Running incremental_caching... PASSED
  Running invalid_symbol_handling... PASSED
  Running rate_limiting_behavior... PASSED

============================================================
📊 DATA FETCHING TEST SUMMARY
============================================================
Total tests: 9
Passed: 9
Failed: 0

🎉 All tests passed!
💡 Note: Cached data is available for future --no-internet runs
```

## 🎯 Test Focus Areas

### ✅ What These Tests Cover
- **Stock Price Fetching**: Yahoo Finance API integration
- **Exchange Rate Fetching**: SBI exchange rate retrieval
- **Company Information**: Corporate data fetching and validation
- **Data Caching**: Persistent cache management and updates
- **Cache Validation**: Data structure and type validation
- **Error Handling**: Invalid symbols and network issues
- **Rate Limiting**: Respectful API usage with delays
- **Offline Mode**: `--no-internet` functionality with cached data
- **Data Persistence**: Cache survives between script runs

### ⚠️ Important Notes
- **Real Network Calls**: These tests make actual API calls
- **Rate Limited**: Tests include delays to respect API limits
- **Cache Building**: First run will be slower as cache is built
- **Internet Required**: Tests automatically check connectivity and exit early if unavailable

### Internet Connection Failure
If internet connectivity is unavailable, the test runner will:
1. Check connectivity to multiple test URLs (Yahoo Finance, Google, HTTPBin)
2. Display a clear error message with the URLs tested
3. Exit immediately with error code 1
4. Prevent misleading "test failures" due to network issues

```
❌ INTERNET CONNECTION ERROR
   Data fetching tests require internet access to validate API integration.
   Please check your network connection and try again.
   Test URLs checked:
   • https://query1.finance.yahoo.com (Yahoo Finance API)
   • https://www.google.com (Basic connectivity)
   • https://httpbin.org/get (HTTP test service)
```

## 📊 Test Data Characteristics

### Symbols Used for Testing
- **MSFT**: Microsoft (reliable, well-known stock)
- **AAPL**: Apple (with `vest_price_optional` override)
- **GOOGL**: Google (added during incremental cache test)
- **INVALID_SYMBOL_XYZ**: Used for error handling tests

### Test Dates
- **MSFT Vest**: 2023-06-15 (10 shares)
- **AAPL Vest**: 2023-03-15 (5 shares with price override)
- **GOOGL Vest**: 2023-04-15 (2 shares, added during incremental test)

### Cache Structure Validated
```json
{
  "stocks": {
    "MSFT": {
      "prices": {"2023-06-15": "335.50", ...},
      "company_info": {"country": "United States", ...},
      "high_low": {"2023-06-15": {"low": "334.00", "high": "337.00"}}
    }
  },
  "exchange_rates": {
    "2023-06-15": "82.75",
    "2023-03-15": "82.90"
  },
  "country_mapping": {
    "United States": 2
  }
}
```

## 🔧 Technical Details

### Test Execution Flow
1. **Setup**: Creates minimal vest.json with test symbols
2. **Fresh Start**: Begins with empty public_data.json
3. **Sequential Tests**: Each test builds on previous cached data
4. **Validation**: Checks data structure, types, and completeness
5. **Cleanup**: Removes temporary files, keeps cache for inspection

### Rate Limiting & API Respect
- **Delays Between Tests**: 1-second pause between test functions
- **Rate Limit Detection**: Tests verify execution time for multiple calls
- **Batch Operations**: Calculator batches API calls when possible
- **Cache First**: Always checks cache before making API calls

### Error Scenarios Tested
- **Invalid Stock Symbols**: Non-existent ticker symbols
- **Network Issues**: Simulated through invalid symbols
- **Partial Cache**: Running offline with incomplete data
- **Data Corruption**: Validation of fetched data structure

## 🚀 Integration with Other Test Suites

These tests complement the existing test framework:
- **Core Tests**: Focus on calculation accuracy (offline)
- **Options Tests**: Focus on CLI behavior (offline)
- **Data Fetching Tests**: Focus on data retrieval (online)

### Run All Test Suites
```bash
# Run comprehensive test suite (includes data fetching)
cd tests && python3 run_all_tests.py

# Run individual suites
cd tests/core-tests && python3 run_core_tests.py          # Offline
cd tests/options-tests && python3 run_options_tests.py    # Offline  
cd tests/data-fetching-tests && python3 run_data_fetching_tests.py  # Online
```

## 📈 Performance Considerations

### Expected Execution Times
- **First Run**: 30-60 seconds (building cache)
- **Subsequent Runs**: 10-20 seconds (using cache)
- **Rate Limiting**: Adds 1-2 seconds per API call
- **Network Latency**: Varies based on connection

### Cache Benefits
- **Faster Subsequent Runs**: Cached data speeds up future executions
- **Offline Capability**: Built cache enables `--no-internet` mode
- **Reduced API Load**: Minimizes external API calls
- **Data Consistency**: Same data across multiple test runs

## 🛡️ Test Safety

### API Usage Guidelines
- **Minimal Calls**: Tests use only necessary API calls
- **Well-Known Symbols**: Uses stable, popular stocks
- **Rate Limiting**: Built-in delays prevent API abuse
- **Cache Reuse**: Maximizes cache usage to minimize new calls

### Data Privacy
- **No Personal Data**: Uses only public stock information
- **Test Symbols**: Uses well-known public companies
- **Temporary Files**: Cleans up generated test files
- **Cache Inspection**: Leaves cache for manual verification

## 🔍 Troubleshooting

### Common Issues
- **Network Timeout**: Increase timeout values in test runner
- **API Rate Limits**: Tests include delays, but external limits may apply
- **Invalid Symbols**: Some tests intentionally use invalid symbols
- **Cache Corruption**: Delete `test_data/public_data.json` to reset

### Debug Mode
```bash
# Run with verbose output for debugging
cd tests/data-fetching-tests
python3 run_data_fetching_tests.py -v  # (if implemented)
```

### Manual Cache Inspection
```bash
# View cached data after tests
cat tests/data-fetching-tests/test_data/public_data.json | jq .
```
