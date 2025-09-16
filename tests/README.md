# Better-Bahn Testing Infrastructure

This directory contains comprehensive test suites for the Better-Bahn application, implementing the testing suggestions from issue #44.

## Test Categories

### Unit Tests

#### 1. Masterdata Loader Tests (`test_masterdata_loader.py`)
- **Malformed YAML handling**: Tests that malformed YAML files raise appropriate exceptions
- **File not found scenarios**: Validates graceful handling when YAML files are missing
- **Schema validation**: Tests EVA number validation and schema extraction
- **Error recovery**: Ensures the application continues working even with masterdata issues

**Key test cases:**
- `test_load_timetable_masterdata_malformed_yaml()` - Verifies malformed YAML returns None
- `test_validate_eva_number_valid_numbers()` - Tests valid 7-digit EVA numbers
- `test_yaml_load_with_circular_reference()` - Handles YAML with circular references

#### 2. Realtime Client Tests (`test_realtime_client.py`)
- **429 rate limiting**: Tests that 429 responses trigger backoff mechanisms
- **Network error handling**: Validates resilience to connection failures
- **JSON parsing errors**: Tests handling of malformed API responses
- **Rate limiting accuracy**: Ensures rate limits are properly enforced

**Key test cases:**
- `test_make_request_429_rate_limit_error()` - Verifies 429 errors are handled gracefully
- `test_consecutive_429_errors()` - Tests multiple consecutive rate limit errors
- `test_real_time_status_extraction()` - Validates delay and cancellation detection

#### 3. Merge Logic Tests (`test_merge_logic.py`)
- **Static trip without realtime**: Tests that trips without realtime data get appropriate status
- **Data preservation**: Ensures enhancement preserves original connection data
- **BahnCard payload creation**: Validates traveller payload generation for all BahnCard types
- **Error handling**: Tests API error scenarios and graceful degradation

**Key test cases:**
- `test_static_trip_without_realtime_unknown_status()` - Verifies no enhancement when realtime unavailable
- `test_create_traveller_payload_bahncard_25_1()` - Tests BahnCard 25 1st class payload creation
- `test_enhance_connection_preserves_original_data()` - Ensures data integrity during enhancement

### Property-Based Tests (`test_property_based.py`)

Uses Hypothesis to generate random test data and verify system invariants:

- **Random timetable generation**: Tests loader round-trip with generated YAML data
- **EVA number validation properties**: Verifies validation works for all 7-digit numbers
- **Input fuzzing**: Tests system robustness with arbitrary inputs
- **YAML parsing scalability**: Ensures parsing performance scales linearly

**Key properties:**
- All 7-digit numbers are valid EVA numbers
- Traveller payloads always have consistent structure
- YAML loading handles any text input gracefully
- Enhancement preserves original data structure

### Performance Tests (`test_performance.py`)

Benchmarks and validates performance requirements:

- **YAML parsing time**: Measures parsing performance for different file sizes
- **Cache hit ratio**: Tests that cache achieves ≥70% hit ratio under typical UI polling
- **Rate limiting accuracy**: Validates rate limiting delays are applied correctly
- **Memory efficiency**: Ensures reasonable memory usage under load

**Key benchmarks:**
- Small YAML parsing: <0.1s
- Medium YAML parsing: <0.5s
- Large YAML parsing: <2.0s
- Cache hit ratio: ≥70% for typical usage patterns
- Rapid refresh handling: 5 requests in proper rate-limited sequence

### Manual QA Tests (`test_manual_qa.py`)

Automated validation of manual QA checklist items:

- **Airplane mode test**: Validates static functionality works without network
- **Rapid refresh handling**: Tests 5 clicks in 5 seconds doesn't exceed rate limits
- **Corrupted YAML handling**: Ensures clear error messages and graceful degradation
- **Error message clarity**: Validates user-friendly error reporting

**Key scenarios:**
- Application works offline with static data
- Rate limiting prevents API overload during rapid clicking
- Corrupted YAML files don't crash the application
- Network errors provide helpful user feedback

## Running Tests

### Run All Tests
```bash
# Run complete test suite
python -m pytest tests/ -v

# Run with coverage reporting
python -m pytest tests/ --cov=main --cov=db_transport_api --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/test_masterdata_loader.py tests/test_realtime_client.py tests/test_merge_logic.py -v

# Property-based tests (with reduced examples for CI)
python -m pytest tests/test_property_based.py -v

# Performance benchmarks
python -m pytest tests/test_performance.py -v

# Manual QA validation
python -m pytest tests/test_manual_qa.py -v
```

### Run Test Runner Script
```bash
# Comprehensive test execution with reporting
python tests/run_all_tests.py
```

## Test Dependencies

Required packages for testing:
```bash
pip install pytest hypothesis psutil
```

- **pytest**: Primary test framework
- **hypothesis**: Property-based testing framework
- **psutil**: System resource monitoring for performance tests

## Test Configuration

### Hypothesis Settings
- Max examples: 20 (CI profile for faster execution)
- Deadline: 1000ms per test
- Database: In-memory for CI environments

### Network Mocking
Tests use `unittest.mock` to simulate:
- Network failures (airplane mode scenarios)
- API rate limiting (429 responses)
- Malformed responses (JSON parsing errors)
- Timeout scenarios

## Continuous Integration

Tests are designed to be CI-friendly:
- No external dependencies (all API calls mocked)
- Reasonable execution times (<2 minutes total)
- Clear pass/fail criteria
- Detailed error reporting

## Test Coverage

The test suite covers:
- **Unit level**: Individual function testing with mocked dependencies
- **Integration level**: Component interaction testing
- **Property level**: Invariant verification with generated data
- **Performance level**: Benchmark validation and scalability
- **QA level**: Manual testing scenario automation

## Expected Results

When all tests pass, the system validates:
1. ✅ Malformed YAML handling works correctly
2. ✅ 429 rate limiting triggers proper backoff
3. ✅ Static trips without realtime get appropriate status
4. ✅ YAML parsing performance meets requirements
5. ✅ Cache hit ratio achieves ≥70% target
6. ✅ Airplane mode scenarios work with static data
7. ✅ Rapid refresh doesn't exceed rate limits
8. ✅ Corrupted YAML produces clear error messages

This comprehensive test suite ensures Better-Bahn is robust, performant, and user-friendly across all operational scenarios.