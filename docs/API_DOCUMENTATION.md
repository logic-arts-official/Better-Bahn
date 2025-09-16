# Better-Bahn API Documentation

## Overview

This document details the API integrations that Better-Bahn uses to gather pricing and connection information. Better-Bahn now integrates with two complementary APIs:

1. **Deutsche Bahn Web API (bahn.de)** - Primary API for pricing and split-ticket analysis
2. **v6.db.transport.rest API** - Real-time journey data, delays, and live information

⚠️ **Important**: The Deutsche Bahn web API endpoints are unofficial and reverse-engineered from browser interactions with bahn.de. These could change without notice.

✅ **Official**: The v6.db.transport.rest API is a community-maintained, stable interface to Deutsche Bahn's HAFAS system.

## Real-time API Integration (v6.db.transport.rest)

### API Base URL
```
https://v6.db.transport.rest
```

### Key Features
- **Live delay information** for trains and connections
- **Station search** with geographic coordinates
- **Journey planning** with real-time updates
- **Cancellation detection** for affected services
- **Rate limiting compliance** (200ms delays)

### Common Headers
```http
User-Agent: Better-Bahn/1.0 (Application Name)
Accept: application/json
```

### Rate Limiting
- **Implementation**: 200ms delay between requests
- **Compliance**: Respectful usage to avoid server overload
- **Fallback**: Graceful degradation when API unavailable

## Deutsche Bahn Web API (Legacy)

### API Base URL
```
https://www.bahn.de/web/api
```

### Common Headers
```http
User-Agent: Mozilla/5.0 (compatible browser string)
Accept: application/json
Content-Type: application/json; charset=UTF-8
Accept-Language: de
```

### Rate Limiting
- **Current Implementation**: 0.5 second delay between requests
- **Recommendation**: Respect server resources, avoid aggressive querying
- **Risk**: Too many requests may result in IP blocking

## Real-time API Endpoints (v6.db.transport.rest)

### 1. Location Search

**Purpose**: Find stations by name or query

#### Endpoint
```http
GET /locations?query={query}&results={count}
```

#### Parameters
- `query`: Station name or search term
- `results`: Maximum number of results (default: 5)

#### Example Request
```http
GET https://v6.db.transport.rest/locations?query=Berlin%20Hbf&results=1
Accept: application/json
```

#### Response Structure
```json
[
  {
    "id": "8011160",
    "name": "Berlin Hbf",
    "type": "station",
    "location": {
      "type": "location",
      "id": "8011160",
      "latitude": 52.524925,
      "longitude": 13.369629
    }
  }
]
```

### 2. Journey Planning

**Purpose**: Get journey options with real-time data

#### Endpoint
```http
GET /journeys?from={fromId}&to={toId}&departure={when}&results={count}&stopovers={bool}
```

#### Parameters
- `from`: Origin station ID
- `to`: Destination station ID  
- `departure`: Departure time (ISO string, optional)
- `results`: Number of journey results (default: 3)
- `stopovers`: Include intermediate stops (default: true)

#### Example Request
```http
GET https://v6.db.transport.rest/journeys?from=8011160&to=8000261&results=3&stopovers=true
Accept: application/json
```

#### Response Structure
```json
{
  "journeys": [
    {
      "type": "journey",
      "legs": [
        {
          "origin": {
            "id": "8011160",
            "name": "Berlin Hbf"
          },
          "destination": {
            "id": "8000261", 
            "name": "München Hbf"
          },
          "departure": {
            "when": "2024-03-15T08:30:00+01:00",
            "delay": 0
          },
          "arrival": {
            "when": "2024-03-15T12:45:00+01:00", 
            "delay": 300
          },
          "cancelled": false
        }
      ],
      "duration": 15900000
    }
  ]
}
```

### 3. Real-time Status Information

**Purpose**: Extract delay and cancellation information from journey data

#### Key Fields for Real-time Status
- `departure.delay`: Departure delay in seconds
- `arrival.delay`: Arrival delay in seconds  
- `cancelled`: Boolean indicating if leg is cancelled
- `duration`: Total journey time in milliseconds

#### Status Processing
```python
def extract_real_time_status(journey_data):
    status = {
        'has_delays': False,
        'total_delay_minutes': 0,
        'cancelled_legs': 0
    }
    
    for leg in journey_data.get('legs', []):
        # Check delays
        if leg.get('departure', {}).get('delay'):
            delay_min = leg['departure']['delay'] // 60
            status['total_delay_minutes'] += delay_min
            status['has_delays'] = True
            
        # Check cancellations
        if leg.get('cancelled'):
            status['cancelled_legs'] += 1
    
    return status
```


## Static Masterdata

### Timetables API Schema (v1.0.213)

Better-Bahn includes static masterdata from the official Deutsche Bahn Timetables API specification for data validation and schema compliance.

**Source**: `data/Timetables-1.0.213.yaml`  
**Format**: OpenAPI 3.0.1 specification  
**Official API Base**: `https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1`

#### Schema Coverage:

1. **Station Information**:
   - EVA station numbers (European station codes)
   - Station names and location data
   - Platform and facility information

2. **Timetable Data Structures**:
   - Connection details and timing
   - Event status and delay information
   - Message and disruption formats

3. **Validation Rules**:
   - EVA number format: 7-digit integers (1000000-9999999)
   - Connection status types: waiting, transition, alternative
   - Event timing in `YYMMddHHmm` format

#### Usage in Better-Bahn:

- **Data Validation**: EVA station numbers validated against official format
- **Schema Compliance**: API responses checked against official structures
- **Error Handling**: Graceful fallback when validation fails
- **Documentation**: Self-documenting API structures for development

## Comparison with HAFAS Standards

Better-Bahn's approach differs from standard HAFAS mgate.exe endpoints:
- **Direct REST-style calls** instead of POST-based RPC calls
- **Browser simulation** rather than official client authentication
- **JSON responses** without HAFAS-specific wrapping
- **Rate limiting required** due to unofficial access

For comparison with standard HAFAS implementations, see [hafas-client's mgate.exe documentation](https://github.com/public-transport/hafas-client/blob/main/docs/hafas-mgate-api.md).

## Base Configuration

### API Base URL
```
https://www.bahn.de/web/api
```

### Common Headers
```http
User-Agent: Mozilla/5.0 (compatible browser string)
Accept: application/json
Content-Type: application/json; charset=UTF-8
Accept-Language: de
```

### Rate Limiting
- **Current Implementation**: 0.5 second delay between requests
- **Recommendation**: Respect server resources, avoid aggressive querying
- **Risk**: Too many requests may result in IP blocking

## API Endpoints

### 1. vbid Resolution

**Purpose**: Convert short vbid links to full connection details

#### Endpoint
```http
GET /angebote/verbindung/{vbid}
```

#### Parameters
- `{vbid}`: The vbid identifier from short links

#### Example Request
```http
GET https://www.bahn.de/web/api/angebote/verbindung/9dd9db26-4ffc-411c-b79c-e82bf5338989
Accept: application/json
User-Agent: Mozilla/5.0
```

#### Response Structure
```json
{
  "hinfahrtRecon": "¶HKI¶T$A=1@O=Berlin...",
  "startOrt": "Berlin Hbf",
  "zielOrt": "München Hbf",
  "hinfahrtDatum": "2024-03-15T08:30:00.000Z",
  "klasse": "KLASSE_2",
  "reisende": [...],
  "verbindungsId": "..."
}
```

#### Key Fields
- `hinfahrtRecon`: Encoded connection string for subsequent API calls
- `startOrt`: Origin station name
- `zielOrt`: Destination station name
- `hinfahrtDatum`: Departure date/time

### 2. Recon Processing

**Purpose**: Get detailed connection information using recon string

#### Endpoint
```http
POST /angebote/recon
```

#### Request Payload
```json
{
  "klasse": "KLASSE_2",
  "reisende": [
    {
      "typ": "ERWACHSENER",
      "ermaessigungen": [
        {
          "art": "BAHNCARD25",
          "klasse": "KLASSE_2"
        }
      ],
      "anzahl": 1,
      "alter": []
    }
  ],
  "ctxRecon": "¶HKI¶T$A=1@O=Berlin...",
  "deutschlandTicketVorhanden": false
}
```

#### Passenger Types
- `ERWACHSENER`: Adult passenger
- `KIND`: Child passenger
- `JUGENDLICHER`: Youth passenger

#### Discount Types
```json
{
  "art": "BAHNCARD25|BAHNCARD50|KEINE_ERMAESSIGUNG",
  "klasse": "KLASSE_1|KLASSE_2|KLASSENLOS"
}
```

#### Response Structure
```json
{
  "verbindungen": [
    {
      "angebotsPreis": {
        "betrag": 49.90,
        "waehrung": "EUR"
      },
      "verbindungsAbschnitte": [
        {
          "verkehrsmittel": {
            "typ": "ICE",
            "nummer": "123",
            "zugattribute": [
              {"key": "9G", "value": "Deutschland-Ticket eligible"}
            ]
          },
          "halte": [
            {
              "id": "8011160",
              "name": "Berlin Hbf",
              "abfahrtsZeitpunkt": "2024-03-15T08:30:00.000Z",
              "ankunftsZeitpunkt": null
            }
          ]
        }
      ]
    }
  ]
}
```

### 3. Timetable Search

**Purpose**: Direct search for connections between stations

#### Endpoint
```http
POST /angebote/fahrplan
```

#### Request Payload
```json
{
  "abfahrtsHalt": "8011160",
  "anfrageZeitpunkt": "2024-03-15T08:30",
  "ankunftsHalt": "8000261",
  "ankunftSuche": "ABFAHRT",
  "klasse": "KLASSE_2",
  "produktgattungen": [
    "ICE", "EC_IC", "IR", "REGIONAL", 
    "SBAHN", "BUS", "SCHIFF", "UBAHN", 
    "TRAM", "ANRUFPFLICHTIG"
  ],
  "reisende": [...],
  "schnelleVerbindungen": true,
  "deutschlandTicketVorhanden": false
}
```

#### Parameters
- `abfahrtsHalt`: Origin station ID
- `ankunftsHalt`: Destination station ID
- `anfrageZeitpunkt`: Search time in ISO format
- `ankunftSuche`: "ABFAHRT" for departure time, "ANKUNFT" for arrival time
- `produktgattungen`: Array of transport types to include

#### Transport Types
- `ICE`: High-speed trains
- `EC_IC`: EuroCity/InterCity
- `IR`: InterRegio
- `REGIONAL`: Regional trains
- `SBAHN`: S-Bahn suburban trains
- `BUS`: Bus connections
- `SCHIFF`: Ferry connections
- `UBAHN`: U-Bahn subway
- `TRAM`: Tram/streetcar
- `ANRUFPFLICHTIG`: On-demand services

## Data Structures

### Station Object
```json
{
  "id": "8011160",
  "name": "Berlin Hbf",
  "coordinates": {
    "lat": 52.525589,
    "lon": 13.369548
  }
}
```

### Connection Object
```json
{
  "verbindungsId": "unique-id",
  "angebotsPreis": {
    "betrag": 49.90,
    "waehrung": "EUR",
    "preisart": "STANDARD"
  },
  "dauer": "PT4H30M",
  "umstiege": 1,
  "verbindungsAbschnitte": [...]
}
```

### Section Object
```json
{
  "verkehrsmittel": {
    "typ": "ICE",
    "nummer": "123",
    "name": "ICE 123",
    "zugattribute": [
      {"key": "9G", "value": "Deutschland-Ticket eligible"}
    ]
  },
  "halte": [
    {
      "id": "8011160",
      "name": "Berlin Hbf",
      "abfahrtsZeitpunkt": "2024-03-15T08:30:00.000Z",
      "ankunftsZeitpunkt": "2024-03-15T08:35:00.000Z",
      "platform": "12"
    }
  ]
}
```

## Deutschland-Ticket Detection

The Deutschland-Ticket eligibility is determined by the presence of specific train attributes:

```json
{
  "zugattribute": [
    {
      "key": "9G",
      "value": "Deutschland-Ticket compatible"
    }
  ]
}
```

When `9G` attribute is present, the segment is covered by Deutschland-Ticket and price is set to €0.

## Error Handling

### Error Response Types

Following patterns from hafas-client, Better-Bahn should implement structured error handling:

#### 1. Network Errors
```python
class DBNetworkError(Exception):
    """Network connectivity issues"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
        self.is_retryable = True
```

#### 2. Rate Limiting Errors  
```python
class DBRateLimitError(Exception):
    """API rate limit exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after
        self.is_retryable = True
```

#### 3. API Response Errors
```python
class DBInvalidResponseError(Exception):
    """Invalid or unexpected API response"""
    def __init__(self, message: str, response_data: Dict = None):
        super().__init__(message)
        self.response_data = response_data
        self.is_retryable = False
```

### Common Error Responses

#### Rate Limiting
```json
{
  "error": "Too Many Requests",
  "code": 429,
  "message": "Rate limit exceeded"
}
```
**Handling**: Implement exponential backoff retry (similar to hafas-client's `withRetrying`)

#### Invalid Station
```json
{
  "error": "Invalid Station",
  "code": 400,
  "message": "Station ID not found"
}
```
**Handling**: Validate station IDs before API calls

#### No Connections Found
```json
{
  "verbindungen": []
}
```
**Handling**: Check for empty results and provide user-friendly messages

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters) 
- `429`: Too Many Requests (rate limited)
- `500`: Internal Server Error
- `503`: Service Unavailable

### Recommended Error Handling Pattern

```python
def make_db_api_request(endpoint: str, payload: Dict, max_retries: int = 3) -> Optional[Dict]:
    """Make API request with comprehensive error handling"""
    
    for attempt in range(max_retries):
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)
                continue
            elif e.response.status_code == 400:
                raise DBInvalidResponseError(f"Invalid request: {e.response.text}")
            elif e.response.status_code >= 500:
                if attempt == max_retries - 1:
                    raise DBNetworkError(f"Server error: {e.response.status_code}")
                time.sleep(1)  # Brief delay before retry
                continue
            else:
                raise DBNetworkError(f"HTTP {e.response.status_code}: {e.response.text}")
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise DBNetworkError(f"Network error: {str(e)}", original_error=e)
            time.sleep(0.5 * (attempt + 1))
    
    return None
```

## Implementation Examples

### Python Implementation

```python
import requests
import time
from typing import Optional, Dict, List

class DBAPIClient:
    BASE_URL = "https://www.bahn.de/web/api"
    
    def __init__(self, rate_limit_delay: float = 0.5):
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Accept-Language': 'de'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make API request with rate limiting and error handling"""
        time.sleep(self.rate_limit_delay)
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def resolve_vbid(self, vbid: str) -> Optional[Dict]:
        """Resolve vbid to connection details"""
        return self._make_request('GET', f'/angebote/verbindung/{vbid}')
    
    def get_connections(self, 
                       from_station: str, 
                       to_station: str, 
                       departure_time: str,
                       traveller_data: List[Dict]) -> Optional[Dict]:
        """Get connections between stations"""
        payload = {
            'abfahrtsHalt': from_station,
            'ankunftsHalt': to_station,
            'anfrageZeitpunkt': departure_time,
            'ankunftSuche': 'ABFAHRT',
            'klasse': 'KLASSE_2',
            'reisende': traveller_data,
            'produktgattungen': ['ICE', 'EC_IC', 'IR', 'REGIONAL'],
            'schnelleVerbindungen': True,
            'deutschlandTicketVorhanden': False
        }
        
        return self._make_request('POST', '/angebote/fahrplan', json=payload)
```

### JavaScript/Flutter Implementation

```dart
class DBAPIClient {
  static const String baseUrl = 'https://www.bahn.de/web/api';
  final http.Client client;
  final Duration rateLimitDelay;
  
  DBAPIClient({http.Client? client, this.rateLimitDelay = const Duration(milliseconds: 500)})
      : client = client ?? http.Client();
  
  Future<Map<String, dynamic>?> _makeRequest(
      String method, String endpoint, {Map<String, dynamic>? body}) async {
    
    await Future.delayed(rateLimitDelay);
    
    try {
      final uri = Uri.parse('$baseUrl$endpoint');
      final headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept-Language': 'de',
      };
      
      http.Response response;
      if (method == 'GET') {
        response = await client.get(uri, headers: headers);
      } else {
        response = await client.post(uri, headers: headers, body: jsonEncode(body));
      }
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        print('API Error: ${response.statusCode} - ${response.body}');
        return null;
      }
    } catch (e) {
      print('Network error: $e');
      return null;
    }
  }
  
  Future<Map<String, dynamic>?> resolveVbid(String vbid) async {
    return _makeRequest('GET', '/angebote/verbindung/$vbid');
  }
}
```

## Best Practices

### 1. Rate Limiting (Inspired by hafas-client patterns)
- **Always implement delays** between requests (minimum 0.5 seconds)
- **Use exponential backoff** for retries (2^attempt * base_delay)
- **Monitor for rate limiting responses** and adjust automatically
- **Implement configurable throttling** similar to hafas-client's `withThrottling`:

```python
class DBAPIThrottler:
    def __init__(self, requests_per_second: float = 2.0):
        self.delay = 1.0 / requests_per_second
        self.last_request = 0
    
    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()
```

### 2. Error Handling (Following hafas-client error patterns)
- **Handle network failures gracefully** with specific error types
- **Provide user-friendly error messages** with actionable guidance
- **Implement retry logic** for transient failures with circuit breaker
- **Preserve error context** for debugging and monitoring:

```python
@dataclass
class APIErrorContext:
    endpoint: str
    request_payload: Dict
    response_status: Optional[int]
    response_headers: Optional[Dict]
    retry_attempt: int
    timestamp: datetime
```

### 3. Data Validation (Enhanced validation patterns)
- **Validate station IDs** before making requests using regex patterns
- **Check response structure** before processing with schema validation
- **Handle missing or null fields** safely with default values
- **Implement input sanitization** for user-provided data

### 4. Caching (Inspired by hafas-client efficiency)
- **Cache station data** to reduce API calls (stations rarely change)
- **Store connection results temporarily** with TTL-based expiration
- **Implement cache invalidation strategies** for real-time accuracy
- **Use request deduplication** to avoid redundant API calls

### 5. Monitoring and Observability
- **Log API response times** and success/failure rates
- **Track request patterns** to optimize rate limiting
- **Monitor for API changes** through response structure validation
- **Implement health checks** for API availability

### 6. Configuration Management (Following hafas-client option patterns)
```python
@dataclass
class DBAPIConfig:
    """Configuration following hafas-client patterns"""
    base_url: str = "https://www.bahn.de/web/api"
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "Better-Bahn/1.0"
    
    # Product filters (similar to hafas-client)
    products: Dict[str, bool] = field(default_factory=lambda: {
        'ICE': True,
        'EC_IC': True,
        'IR': True,
        'REGIONAL': True,
        'SBAHN': True,
        'BUS': False
    })
```

## Security Considerations

### 1. No Authentication Required
- APIs are publicly accessible
- No API keys or tokens needed
- Rate limiting is the primary protection

### 2. Data Privacy
- Don't store unnecessary user data
- Process requests locally when possible
- Respect user privacy preferences

### 3. Ethical Usage
- Respect server resources
- Don't abuse rate limits
- Consider impact on DB infrastructure

## Troubleshooting

### Common Issues

#### 1. Empty Response
```json
{"verbindungen": []}
```
**Causes**: Invalid station IDs, no connections available, time too far in future
**Solutions**: Validate inputs, try different times, check station existence

#### 2. Rate Limiting
**Symptoms**: 429 status codes, blocked requests
**Solutions**: Increase delays, implement exponential backoff, use proxy rotation

#### 3. Changed API Structure
**Symptoms**: Missing fields, unexpected response format
**Solutions**: Update parsing logic, add defensive programming, monitor for changes

### Debugging Tips

1. **Log All Requests**: Keep track of what you're sending
2. **Inspect Responses**: Understand the data structure
3. **Test with Browser**: Compare with manual bahn.de usage
4. **Monitor Network**: Use tools like mitmproxy to inspect traffic

## Limitations

1. **Unofficial Status**: No guarantees of stability or availability
2. **Rate Limits**: Aggressive usage may be blocked
3. **Geographic Scope**: Limited to German railway network
4. **Language**: Responses primarily in German
5. **Real-time Data**: Limited access to live delay information

This API documentation reflects the current understanding of Deutsche Bahn's web interfaces. Always test thoroughly and implement robust error handling when using these endpoints.