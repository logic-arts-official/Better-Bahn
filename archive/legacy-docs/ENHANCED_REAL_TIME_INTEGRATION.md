# Better-Bahn Real-time API Integration

## Overview

This document describes the comprehensive real-time API integration enhancements for Better-Bahn, implementing all acceptance criteria for production-ready real-time data processing.

## Features Implemented

### ✅ Configurable Base URL & Timeout
- **Environment Variables**: Configure via `BETTER_BAHN_API_URL`, `BETTER_BAHN_TIMEOUT`
- **Configuration File**: JSON-based configuration support
- **Default Values**: Production-ready defaults with environment override capability

### ✅ Advanced Rate Limiting
- **Exponential Backoff**: Configurable with `BETTER_BAHN_EXPONENTIAL_BACKOFF=true`
- **Retry-After Header Support**: Respects HTTP 429 Retry-After headers
- **Max Backoff Delay**: Configurable maximum wait time (default: 60 seconds)
- **Rate Limit Delay**: Base delay between requests (default: 200ms)

### ✅ Comprehensive Caching Layer
- **Memory Cache**: In-memory LRU cache with configurable TTL (default: 30 seconds)
- **Disk Cache**: Optional persistent cache for offline fallback
- **Cache Statistics**: Hit rates, size tracking, performance metrics
- **Intelligent TTL**: Different cache durations for different data types

### ✅ Graceful Degradation
- **Stale Data Fallback**: Uses expired cache data when API unavailable
- **Feature Flag**: Runtime disable via `BETTER_BAHN_ENABLE_REALTIME=false`
- **Error Handling**: Continues operation without real-time data
- **Status Indicators**: Clear messaging about data freshness

### ✅ Comprehensive Logging & Metrics
- **Latency Buckets**: Request timing distribution tracking
- **HTTP Status Distribution**: Success/error rate monitoring  
- **Cache Hit Rate Tracking**: Performance optimization insights
- **Error Classification**: Categorized error tracking and reporting

### ✅ Complete Test Matrix
- **Mock 200/429/500/timeout**: All HTTP response scenarios covered
- **Integration Tests**: Live API connectivity testing (optional)
- **Cache Testing**: Hit/miss scenarios and expiration validation
- **Configuration Testing**: Environment and file-based config validation

### ✅ Security Considerations
- **No Secrets Required**: Uses public API endpoints
- **Rate Limiting Compliance**: Respectful API usage patterns
- **Input Validation**: Proper sanitization of user inputs
- **Error Information**: Limited error details in production

## Configuration

### Environment Variables

```bash
# API Configuration
export BETTER_BAHN_API_URL="https://v6.db.transport.rest"
export BETTER_BAHN_TIMEOUT=30
export BETTER_BAHN_RATE_LIMIT=0.2
export BETTER_BAHN_MAX_RETRIES=3
export BETTER_BAHN_EXPONENTIAL_BACKOFF=true
export BETTER_BAHN_MAX_BACKOFF=60.0
export BETTER_BAHN_RESPECT_RETRY_AFTER=true
export BETTER_BAHN_ENABLE_REALTIME=true

# Cache Configuration  
export BETTER_BAHN_MEMORY_CACHE=true
export BETTER_BAHN_MEMORY_CACHE_TTL=30
export BETTER_BAHN_MEMORY_CACHE_SIZE=1000
export BETTER_BAHN_DISK_CACHE=false
export BETTER_BAHN_DISK_CACHE_TTL=300
export BETTER_BAHN_DISK_CACHE_DIR="/tmp/better_bahn_cache"

# Logging Configuration
export BETTER_BAHN_METRICS=true
export BETTER_BAHN_LOG_LEVEL=INFO
export BETTER_BAHN_TRACK_LATENCY=true
export BETTER_BAHN_TRACK_STATUS=true
export BETTER_BAHN_TRACK_CACHE=true
```

### Configuration File

Create `better_bahn_config.json`:

```json
{
  "api": {
    "base_url": "https://v6.db.transport.rest",
    "timeout": 30,
    "rate_limit_delay": 0.2,
    "max_retries": 3,
    "exponential_backoff": true,
    "max_backoff_delay": 60.0,
    "respect_retry_after": true,
    "enable_realtime": true
  },
  "cache": {
    "enable_memory_cache": true,
    "memory_cache_ttl": 30,
    "memory_cache_max_size": 1000,
    "enable_disk_cache": false,
    "disk_cache_ttl": 300,
    "disk_cache_dir": "/tmp/better_bahn_cache"
  },
  "logging": {
    "enable_metrics": true,
    "log_level": "INFO",
    "track_latency": true,
    "track_status_codes": true,
    "track_cache_hits": true
  }
}
```

Use with: `export BETTER_BAHN_CONFIG_FILE=better_bahn_config.json`

## Usage Examples

### Basic Usage (with real-time data)

```bash
# Default behavior includes real-time enhancements
python main.py "https://www.bahn.de/buchung/start?vbid=abc123" --age 30
```

### Disable Real-time Features

```bash
# Use only static bahn.de data
python main.py "https://www.bahn.de/buchung/start?vbid=abc123" --no-real-time
```

### Configuration File Usage

```bash
# Use custom configuration
export BETTER_BAHN_CONFIG_FILE=my_config.json
python main.py "https://www.bahn.de/buchung/start?vbid=abc123"
```

### Enable Disk Cache for Offline Support

```bash
export BETTER_BAHN_DISK_CACHE=true
export BETTER_BAHN_DISK_CACHE_DIR="/home/user/.cache/better_bahn"
python main.py "https://www.bahn.de/buchung/start?vbid=abc123"
```

## Real-time Data Features

### Enhanced Journey Information
- **Live Delays**: Minute-accurate delay information
- **Cancellation Detection**: Identifies cancelled services
- **Platform Changes**: Real-time platform updates (when available)
- **Service Disruptions**: Integration with disruption alerts

### Performance Optimization
- **Intelligent Caching**: Frequently requested routes cached longer
- **Request Deduplication**: Prevents redundant API calls
- **Batch Processing**: Efficient data retrieval patterns
- **Graceful Timeouts**: Non-blocking real-time requests

### User Experience
- **Status Indicators**: Clear real-time data availability status
- **Performance Metrics**: Cache efficiency and API latency display
- **Fallback Messaging**: Informative messages when real-time unavailable
- **Progressive Enhancement**: Works with or without real-time data

## Monitoring & Observability

### Metrics Collected

```python
# Example metrics output
{
  "latency": {
    "count": 45,
    "mean_ms": 287.3,
    "p95_ms": 450.2,
    "p99_ms": 890.1
  },
  "status_codes": {
    "success_rate": 0.956,
    "error_rate": 0.044,
    "distribution": {
      "200": 43,
      "429": 1,
      "500": 1
    }
  },
  "cache": {
    "hit_rate": 0.734,
    "hits": 33,
    "misses": 12
  }
}
```

### Performance Tuning

**High Traffic Scenarios:**
- Increase memory cache size: `BETTER_BAHN_MEMORY_CACHE_SIZE=5000`
- Enable disk cache: `BETTER_BAHN_DISK_CACHE=true`
- Reduce rate limit: `BETTER_BAHN_RATE_LIMIT=0.1`

**Low Bandwidth Environments:**
- Disable real-time: `BETTER_BAHN_ENABLE_REALTIME=false`
- Increase cache TTL: `BETTER_BAHN_MEMORY_CACHE_TTL=120`
- Enable disk cache for offline use

**Development/Testing:**
- Faster rate limiting: `BETTER_BAHN_RATE_LIMIT=0.05`
- Detailed logging: `BETTER_BAHN_LOG_LEVEL=DEBUG`
- Enable all metrics: `BETTER_BAHN_METRICS=true`

## Testing

### Automated Test Matrix

```bash
# Run full test suite
python test_real_time_integration.py

# Run integration tests with live API
export BETTER_BAHN_INTEGRATION_TESTS=true
python test_real_time_integration.py
```

### Manual Testing Scenarios

1. **Normal Operation**: Test with valid journey URLs
2. **Rate Limiting**: Test with rapid successive requests
3. **Network Issues**: Test with network disconnection
4. **Configuration**: Test with various config combinations
5. **Cache Behavior**: Test cache hits/misses and expiration

## Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   main.py       │    │  Configuration   │    │  API Client     │
│  (CLI Entry)    │───▶│   Management     │───▶│   (Enhanced)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Split Ticket    │    │  Logging &      │    │  Caching        │
│ Analysis        │    │  Metrics        │    │  Layer          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Integration Points

1. **CLI Integration**: Enhanced command-line interface with real-time options
2. **Configuration Layer**: Flexible environment and file-based configuration
3. **API Client**: Production-ready HTTP client with advanced features
4. **Caching System**: Multi-tier caching for performance and offline support
5. **Metrics Collection**: Comprehensive observability and monitoring
6. **Error Handling**: Graceful degradation and user-friendly error messages

## Future Enhancements

The architecture supports easy extension for:

1. **Additional APIs**: Integration with other transport data sources
2. **Enhanced Caching**: Redis/database backend for shared cache
3. **Real-time Updates**: WebSocket connections for live updates
4. **Mobile Integration**: Flutter app integration with same backend
5. **Analytics**: Journey pattern analysis and optimization suggestions

## Migration Guide

### From Legacy Integration

If upgrading from the basic real-time integration:

1. **Update Dependencies**: No new dependencies required
2. **Configuration**: Add environment variables or config file
3. **Features**: All existing functionality preserved
4. **Testing**: Run test matrix to validate integration

### Backward Compatibility

- All existing command-line options work unchanged
- Default behavior includes real-time enhancements
- `--no-real-time` flag disables new features
- Configuration is optional (sensible defaults provided)
- No breaking changes to existing workflows

## Support & Troubleshooting

### Common Issues

**Real-time data unavailable:**
- Check network connectivity
- Verify API endpoint accessibility
- Review rate limiting configuration
- Check feature flag status

**Performance issues:**
- Monitor cache hit rates
- Adjust cache sizes and TTL values
- Review rate limiting settings
- Check disk space for disk cache

**Configuration problems:**
- Validate JSON syntax in config files
- Check environment variable names
- Verify file paths and permissions
- Review log output for configuration errors

### Debug Mode

```bash
export BETTER_BAHN_LOG_LEVEL=DEBUG
export BETTER_BAHN_METRICS=true
python main.py "https://www.bahn.de/buchung/start?vbid=abc123"
```

This provides detailed logging of:
- Configuration loading
- API request/response cycles
- Cache operations
- Error conditions
- Performance metrics