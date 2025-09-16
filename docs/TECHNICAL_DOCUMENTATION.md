# Better-Bahn Technical Documentation

## Architecture Overview

Better-Bahn is a dual-platform application designed to find cheaper split-ticket combinations for Deutsche Bahn (German Railway) journeys. The project consists of two main components:

1. **Python CLI Tool** (`main.py`) - Core logic and API interactions
2. **Flutter Mobile App** (`flutter-app/`) - User-friendly mobile interface

## Core Functionality

### Split-Ticket Analysis Algorithm

The application implements a dynamic programming approach to find the optimal combination of tickets:

1. **Route Extraction**: Parses DB URLs (both short vbid links and long URLs) to extract journey details
2. **Station Discovery**: Identifies all intermediate stations along the route
3. **Price Matrix**: Queries prices for all possible sub-routes between stations
4. **Optimization**: Uses dynamic programming to find the cheapest combination of tickets

### API Integration Strategy

**Important**: Better-Bahn does not use official Deutsche Bahn APIs. Instead, it simulates browser requests to `bahn.de` to gather pricing data.

#### Request Flow:
1. **URL Resolution**: 
   - Short links (vbid) → `/web/api/angebote/verbindung/{vbid}`
   - Long links → Direct parsing of route parameters

2. **Connection Details**: 
   - Endpoint: `/web/api/angebote/fahrplan`
   - Payload includes traveler data, BahnCard discounts, Deutschland-Ticket status

3. **Price Discovery**:
   - Queries all possible sub-routes between stations
   - Rate limiting: 0.5 second delay between requests
   - Deutschland-Ticket compatibility checking

## Technical Components

### Python Backend (`main.py`)

#### Key Functions:

- `load_timetable_masterdata()`: Loads static timetable schema and metadata from YAML
- `get_station_schema()`: Provides access to Deutsche Bahn API schema definitions
- `validate_eva_number()`: Validates EVA station numbers against expected format
- `resolve_vbid_to_connection()`: Converts short links to full connection data
- `get_connection_details()`: Fetches route and pricing information
- `get_segment_data()`: Analyzes individual route segments
- `find_cheapest_split()`: Dynamic programming optimization algorithm
- `generate_booking_link()`: Creates deep links for ticket purchasing

#### Supported Features:
- **Static Masterdata**: Timetables API v1.0.213 schema definitions and validation
- **Station Data Validation**: EVA number format validation and schema compliance
- **BahnCard discounts** (25/50, 1st/2nd class)
- **Deutschland-Ticket integration**
- **Age-based pricing**
- **Direct booking link generation**

### Flutter Frontend

#### Architecture:
- Material Design 3 with DB corporate colors
- Responsive design for mobile devices
- HTTP client for API communication
- URL launcher for external booking links

#### Key Features:
- Link input and validation
- Settings for BahnCard and Deutschland-Ticket
- Results display with savings calculation
- Direct booking link integration

## Data Flow

```
User Input (DB URL) 
    ↓
URL Parsing & Validation
    ↓
API Request to bahn.de
    ↓
Route & Station Extraction
    ↓
Price Matrix Generation (N² API calls)
    ↓
Dynamic Programming Optimization
    ↓
Results & Booking Links
```

## Rate Limiting & Performance

### Current Limitations:
- 0.5 second delay between API requests
- No proxy rotation or advanced rate limiting evasion
- Sequential processing of price queries

### Recommended Improvements (Based on hafas-client Patterns):

#### Configurable Rate Limiting:
```python
class DBAPIClient:
    def __init__(self, rate_limit_delay=0.5, max_retries=3):
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        
    def _make_request_with_backoff(self, method, url, **kwargs):
        """Make request with exponential backoff retry"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = (2 ** attempt) * self.rate_limit_delay
                    time.sleep(wait_time)
                    continue
                raise
        raise DBRateLimitError("Max retries exceeded")
```

#### Advanced Rate Limiting Features:
- **Exponential backoff**: Automatically increase delays on rate limit errors
- **Configurable thresholds**: Allow users to adjust request frequency
- **Request queuing**: Queue requests to avoid overwhelming the API
- **Circuit breaker pattern**: Temporarily halt requests after consecutive failures

### Performance Characteristics:
- For N stations: O(N²) API calls required
- Processing time: ~(N² × 0.5) seconds minimum
- Memory usage: O(N²) for price matrix storage
- **New**: Retry overhead: Up to 3x processing time on failures
- **New**: Caching potential: Reduce duplicate requests by 50-80%

## Security Considerations

### Web Scraping Ethics:
- Simulates legitimate browser requests
- Respects rate limits to avoid server overload
- No attempt to bypass anti-bot measures
- Distributes load across individual user devices

### Data Privacy:
- No data stored on external servers
- All processing occurs locally
- No user tracking or analytics
- No authentication or user accounts required

## Error Handling

### Current Implementation:
- Network request timeouts with basic `requests.RequestException` handling
- Invalid URL detection and user feedback
- Missing price data graceful degradation with `None` returns
- Connection failure recovery through silent failure handling

### Recommended Improvements (Based on hafas-client Analysis):

#### Structured Error Hierarchy:
```python
class DBAPIError(Exception):
    """Base class for all DB API related errors"""
    def __init__(self, message: str, code: str = None, is_server_error: bool = False):
        super().__init__(message)
        self.code = code
        self.is_server_error = is_server_error
        self.is_db_error = True

class DBConnectionNotFoundError(DBAPIError):
    """Raised when no connections found between stations"""
    pass

class DBRateLimitError(DBAPIError):
    """Raised when API rate limit is exceeded"""
    pass

class DBInvalidStationError(DBAPIError):
    """Raised when station ID is invalid"""
    pass
```

#### Enhanced Error Handling Pattern:
```python
def get_connection_details_enhanced(from_id, to_id, date, time, traveller_payload, deutschland_ticket):
    """Enhanced version with structured error handling"""
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("verbindungen"):
            raise DBConnectionNotFoundError(f"No connections found from {from_id} to {to_id}")
            
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            raise DBRateLimitError("API rate limit exceeded")
        elif e.response.status_code == 400:
            raise DBInvalidStationError(f"Invalid station parameters: {from_id}, {to_id}")
        else:
            raise DBAPIError(f"HTTP {e.response.status_code}: {e.response.text}",
                           is_server_error=e.response.status_code >= 500)
    except requests.exceptions.RequestException as e:
        raise DBAPIError(f"Network error: {str(e)}")
```

### Logging & Debugging:
- Detailed console output for troubleshooting
- Step-by-step analysis progress reporting
- Clear error messages for common issues
- **New**: Structured error codes for programmatic handling
- **New**: Error context preservation for debugging

## Static Masterdata Integration

### Timetables API Schema (v1.0.213)

The application integrates static masterdata from the Deutsche Bahn Timetables API specification:

**Location**: `data/Timetables-1.0.213.yaml`
**Format**: OpenAPI 3.0.1 specification (YAML)
**Version**: 1.0.213
**Purpose**: Schema definitions for station data, timetable structures, and API validation

#### Key Schema Components:

1. **Station Data (`station`)**:
   - EVA station numbers (7-digit format)
   - Station names and metadata
   - Location coordinates and identifiers

2. **Timetable Structures (`timetable`, `timetableStop`)**:
   - Connection information
   - Event timing and status
   - Platform and track details

3. **Validation Schemas**:
   - `connectionStatus`: Connection state validation (waiting, transition, alternative)
   - `eventStatus`: Departure/arrival event states
   - `delaySource`: Delay information sources

#### Masterdata Functions:

- **`load_timetable_masterdata()`**: Loads the complete OpenAPI specification
- **`get_station_schema()`**: Extracts schema definitions for validation
- **`validate_eva_number()`**: Validates EVA station numbers (1000000-9999999)

#### Error Handling:
- Graceful degradation when masterdata is unavailable
- YAML parsing error recovery
- Schema validation with fallback to basic validation

#### Integration Benefits:
- **Data Validation**: Ensures station data meets Deutsche Bahn standards
- **Schema Compliance**: API response validation against official schemas
- **Future-Proofing**: Ready for enhanced validation and station lookup features
- **Documentation**: Self-documenting API structures and formats

## Deployment Architecture

### Advantages of Local Processing:
1. **No Server Costs**: Eliminates hosting and maintenance expenses
2. **Scalability**: Load distributed across user devices
3. **Privacy**: No central data collection point
4. **Reliability**: Not dependent on server uptime
5. **Rate Limit Avoidance**: Individual user requests less likely to be blocked

### Distribution Channels:
- GitHub Releases for Android APK
- Python package for CLI usage
- Source code for custom builds

## Code Quality Assessment

### Strengths:
- Clear separation of concerns
- Comprehensive error handling
- Well-documented API interactions
- User-friendly command-line interface

### Areas for Improvement:
- Limited unit test coverage
- Hard-coded API endpoints
- Minimal configuration options
- No caching mechanism for repeated queries

## Future Enhancement Opportunities

### Technical Improvements (Inspired by hafas-client):
1. **Modular API Client Architecture**: Create a dedicated `DBAPIClient` class with consistent interfaces
2. **Structured Error Handling**: Implement error hierarchy similar to hafas-client's `HafasError` family
3. **Configurable Rate Limiting**: Add `withThrottling` and `withRetrying` patterns for flexible rate limiting
4. **Request/Response Logging**: Add `logRequest` and `logResponse` hooks for debugging
5. **Caching System**: Store pricing data to reduce API calls with cache invalidation
6. **Parallel Processing**: Concurrent price queries where possible (respecting rate limits)
7. **Configuration Management**: User-customizable settings following hafas-client's option pattern
8. **Comprehensive Test Coverage**: Unit and integration tests with mock API responses

### API Integration Enhancements:
1. **Standardized Data Structures**: Define clear data classes for connections, stations, and prices
2. **Type Hints and Validation**: Add comprehensive type annotations and input validation
3. **Authentication Handling**: Prepare for potential future authentication requirements
4. **Profile System**: Implement endpoint-specific profiles similar to hafas-client
5. **Response Parsing**: Robust parsing with fallback handling for API changes

### Feature Additions:
1. **Historical Price Tracking**: Monitor price trends over time with structured storage
2. **Schedule Integration**: Consider departure times in optimization with real-time data
3. **Multi-passenger Support**: Group booking optimization with traveller management
4. **Alternative Route Suggestions**: Compare different journey paths using route analysis
5. **Notification System**: Alert users to price changes with configurable thresholds
6. **Real-time Updates**: Integration with live delay and disruption information

### Documentation Improvements (Following hafas-client Structure):
1. **Method-specific Documentation**: Create individual files for each API endpoint
2. **Comprehensive Error Guide**: Document all error types with handling examples
3. **Usage Patterns Guide**: Show common integration patterns and best practices
4. **Migration Documentation**: Version-specific upgrade guides for future changes