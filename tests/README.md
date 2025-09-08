# FA Calculator Test Suite

This directory contains the comprehensive test suite for the Foreign Assets Schedule Calculator, providing validation across multiple dimensions of functionality.

## 🎯 Test Suite Overview

### **24 Total Test Scenarios** across **3 Test Suites**

| Test Suite | Scenarios | Focus Area | Network | Runtime |
|------------|-----------|------------|---------|---------|
| **Core Tests** | 5 | Calculation accuracy & correctness | Offline | ~10s |
| **Options Tests** | 10 | CLI behavior & error handling | Offline | ~15s |
| **Data Fetching Tests** | 9 | Network operations & caching | Online | ~60s |

## 🚀 Quick Start

### **Recommended: Run Offline Tests (Fast)**
```bash
cd tests
python3 run_all_tests.py --offline
```
**Result**: 15 test scenarios in ~25 seconds (no network calls)

### **Comprehensive: Run All Tests (Thorough)**
```bash
cd tests  
python3 run_all_tests.py
```
**Result**: 24 test scenarios in ~90 seconds (includes network validation)

### **Individual Test Suites**
```bash
# Core functionality (calculation accuracy)
cd tests/core-tests && python3 run_core_tests.py

# Command-line options (CLI behavior) 
cd tests/options-tests && python3 run_options_tests.py

# Data fetching (network & caching)
cd tests/data-fetching-tests && python3 run_data_fetching_tests.py
```

## 📊 Test Coverage Matrix

### ✅ **Core Tests** (Offline, Fast)
| Test | Scenario | Purpose |
|------|----------|---------|
| data1 | Simple vest, no sales | Basic calculation validation |
| data2 | Vest with price override | `vest_price_optional` functionality |
| data3 | Partial stock sales | Sale proceeds & remaining shares |
| data4 | Multiple vests & stocks | Complex multi-lot scenarios |
| data5 | Peak after partial sale | Advanced timing dependencies |

### ✅ **Options Tests** (Offline, Fast)
| Test | Option | Purpose |
|------|--------|---------|
| help_option | `--help` | Usage information display |
| verbose_option | `-v/--verbose` | Detailed output validation |
| skip_validation_option | `-x` | Performance option testing |
| skip_sorting_option | `-y` | File handling option testing |
| data_option | `--data` | Custom directory functionality |
| invalid_year | Invalid args | Error handling validation |
| missing_data_directory | Bad paths | File system error handling |
| combined_options | `-v -x -y` | Option interaction testing |
| clean_up_pii_help | PII script help | Related script integration |
| clean_up_pii_data_option | PII script options | Related script functionality |

### ✅ **Data Fetching Tests** (Online, Comprehensive)
| Test | Network Operation | Purpose |
|------|-------------------|---------|
| stock_price_fetching | Yahoo Finance API | Price retrieval & caching |
| exchange_rate_fetching | SBI exchange rates | Currency conversion data |
| cache_persistence | File system caching | Data persistence validation |
| vest_price_optional_override | Price override logic | Optional price handling |
| no_internet_with_partial_cache | Offline mode | Cache-only functionality |
| data_validation | Data structure checks | API response validation |
| incremental_caching | Cache updates | Incremental data addition |
| invalid_symbol_handling | Error scenarios | Invalid input handling |
| rate_limiting_behavior | API respect | Rate limiting compliance |

## 🎨 Test Philosophy

### **Three-Tier Validation Strategy**

1. **🎯 Core Tests**: Validate that the calculator produces correct results
2. **🔧 Options Tests**: Validate that the CLI behaves correctly  
3. **🌐 Data Fetching Tests**: Validate that data retrieval works correctly

### **Design Principles**

- **Fast Feedback**: Offline tests run quickly for rapid development
- **Comprehensive Coverage**: Online tests validate real-world scenarios
- **Isolated Testing**: Each test suite can run independently
- **Reproducible Results**: Deterministic test data and caching
- **Respectful Testing**: Network tests include rate limiting
- **Clear Reporting**: Detailed pass/fail reporting with error details

## 🔧 Test Data Management

### **Core Tests**
- **Pre-built fixtures**: Complete test scenarios with expected outputs
- **Cached market data**: Full year of daily prices for offline testing
- **Deterministic results**: Same input always produces same output

### **Options Tests**  
- **Auto-generated data**: Simple test data created by test runner
- **Minimal complexity**: Focus on CLI behavior, not calculation accuracy
- **Temporary files**: Clean up after each test run

### **Data Fetching Tests**
- **Real API calls**: Actual network requests to validate connectivity
- **Cache building**: Tests build real cache data for future use
- **Rate limited**: Respectful delays between API calls
- **Error simulation**: Invalid symbols to test error handling

## 🚨 Important Notes

### **Network Requirements**
- **Core & Options Tests**: No internet required (use `--no-internet`)
- **Data Fetching Tests**: Internet connection required for API calls
- **Rate Limiting**: Data fetching tests include delays (1-2 seconds per call)
- **API Respect**: Tests use well-known symbols and minimal calls

### **Execution Times**
- **Offline Mode** (`--offline`): ~25 seconds for 15 tests
- **Full Suite**: ~90 seconds for 24 tests (includes network delays)
- **First Run**: Data fetching tests slower when building cache
- **Subsequent Runs**: Faster due to cached data reuse

### **Cache Benefits**
- **Faster Subsequent Runs**: Built cache enables `--no-internet` mode
- **Offline Development**: Core functionality works without network
- **Consistent Results**: Same cached data produces identical outputs
- **Real Data**: Cache contains actual market data for validation

## 🎉 Success Criteria

### **All Tests Pass**
```
🎉 ALL TEST SUITES PASSED!
The FA Calculator is ready for use.
```

### **Individual Suite Success**
- **Core Tests**: All 5 calculation scenarios pass
- **Options Tests**: All 10 CLI behaviors work correctly  
- **Data Fetching Tests**: All 9 network operations succeed

### **Failure Handling**
- **Clear Error Messages**: Specific failure reasons provided
- **Exit Codes**: Proper codes for CI/CD integration
- **Isolation**: One failed test doesn't affect others
- **Debugging Info**: Detailed output for troubleshooting

## 🔄 Integration with Development

### **Pre-Commit Validation**
```bash
# Quick validation before committing changes
cd tests && python3 run_all_tests.py --offline
```

### **Full Validation**
```bash
# Comprehensive validation before releases
cd tests && python3 run_all_tests.py
```

### **Continuous Integration**
- **Offline Tests**: Can run in CI without network access
- **Full Tests**: Require network access for complete validation
- **Exit Codes**: Proper success/failure signaling for automation
- **Detailed Logging**: Complete test output for debugging

This test suite ensures the FA Calculator is robust, reliable, and ready for real-world usage across all its functionality dimensions.
