# Implementation Recommendations: hafas-client Integration Patterns

## Summary of Recommendations

Based on the analysis of `public-transport/hafas-client`, this document provides specific implementation recommendations for improving Better-Bahn's DB API integration, error handling, and overall architecture.

## Priority 1: Immediate Improvements

### 1. Structured Error Handling

**Current State**: Basic `requests.RequestException` handling with silent failures.

**Recommended Implementation**:

Create a new file `better_bahn/errors.py`:

```python
"""
DB API Error Types - Inspired by hafas-client error hierarchy
"""
from typing import Optional, Dict, Any
from enum import Enum

class DBAPIErrorCode(Enum):
    """Standardized error codes for DB API interactions"""
    NETWORK_ERROR = "NETWORK_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_STATION = "INVALID_STATION"
    NO_CONNECTIONS = "NO_CONNECTIONS"
    INVALID_VBID = "INVALID_VBID"
    SERVER_ERROR = "SERVER_ERROR"
    AUTHENTICATION_ERROR = "AUTH_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"

class DBAPIError(Exception):
    """Base class for all DB API related errors"""
    
    def __init__(self, message: str, code: Optional[str] = None, 
                 is_server_error: bool = False, context: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.is_server_error = is_server_error
        self.is_db_error = True
        self.context = context or {}

class DBNetworkError(DBAPIError):
    """Network connectivity or timeout errors"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, code=DBAPIErrorCode.NETWORK_ERROR.value)
        self.original_error = original_error
        self.is_retryable = True

class DBRateLimitError(DBAPIError):
    """API rate limit exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        super().__init__("Rate limit exceeded", code=DBAPIErrorCode.RATE_LIMITED.value)
        self.retry_after = retry_after
        self.is_retryable = True

class DBConnectionNotFoundError(DBAPIError):
    """No connections found between specified stations"""
    def __init__(self, from_station: str, to_station: str):
        super().__init__(
            f"No connections found from {from_station} to {to_station}",
            code=DBAPIErrorCode.NO_CONNECTIONS.value,
            context={"from_station": from_station, "to_station": to_station}
        )

class DBInvalidStationError(DBAPIError):
    """Invalid station ID provided"""
    def __init__(self, station_id: str):
        super().__init__(
            f"Invalid station ID: {station_id}",
            code=DBAPIErrorCode.INVALID_STATION.value,
            context={"station_id": station_id}
        )

class DBInvalidVbidError(DBAPIError):
    """Invalid vbid format or expired vbid"""
    def __init__(self, vbid: str):
        super().__init__(
            f"Invalid or expired vbid: {vbid}",
            code=DBAPIErrorCode.INVALID_VBID.value,
            context={"vbid": vbid}
        )
```

### 2. Modular API Client

**Current State**: Functions scattered throughout `main.py`.

**Recommended Implementation**:

Create a new file `better_bahn/db_api_client.py`:

```python
"""
DB API Client - Inspired by hafas-client architecture
"""
import time
import requests
from typing import Optional, Dict, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .errors import (
    DBAPIError, DBNetworkError, DBRateLimitError, 
    DBConnectionNotFoundError, DBInvalidStationError, DBInvalidVbidError
)

@dataclass
class DBAPIConfig:
    """Configuration for DB API client - following hafas-client pattern"""
    base_url: str = "https://www.bahn.de/web/api"
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "Better-Bahn/1.0"
    
    # Product filters (similar to hafas-client products)
    products: Dict[str, bool] = field(default_factory=lambda: {
        'ICE': True,
        'EC_IC': True,
        'IR': True,
        'REGIONAL': True,
        'SBAHN': True,
        'BUS': False,
        'SCHIFF': False,
        'UBAHN': False,
        'TRAM': False
    })

class DBAPIClient:
    """
    Main API client for Deutsche Bahn endpoints
    Inspired by hafas-client's createClient pattern
    """
    
    def __init__(self, config: Optional[DBAPIConfig] = None):
        self.config = config or DBAPIConfig()
        self.session = requests.Session()
        self._setup_session()
        self._last_request_time = 0
    
    def _setup_session(self):
        """Configure session with appropriate headers"""
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json',
            'Accept-Language': 'de',
            'Content-Type': 'application/json; charset=UTF-8'
        })
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting similar to hafas-client throttling"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make API request with error handling and retries
        Similar to hafas-client's request pattern
        """
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                self._wait_for_rate_limit()
                
                response = self.session.request(
                    method, url, timeout=self.config.timeout, **kwargs
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = (2 ** attempt) * self.config.rate_limit_delay
                    time.sleep(wait_time)
                    continue
                elif e.response.status_code == 400:
                    raise DBAPIError(
                        f"Invalid request: {e.response.text}",
                        code="INVALID_REQUEST"
                    )
                elif e.response.status_code >= 500:
                    if attempt == self.config.max_retries - 1:
                        raise DBAPIError(
                            f"Server error: {e.response.status_code}",
                            is_server_error=True
                        )
                    time.sleep(1)  # Brief delay before retry
                    continue
                else:
                    raise DBAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise DBNetworkError(f"Network error: {str(e)}", original_error=e)
                time.sleep(0.5 * (attempt + 1))
        
        raise DBNetworkError("Max retries exceeded")
    
    def resolve_vbid(self, vbid: str) -> Dict:
        """
        Resolve vbid to connection details
        Enhanced with proper error handling
        """
        try:
            data = self._make_request('GET', f'/angebote/verbindung/{vbid}')
            
            if not data.get("hinfahrtRecon"):
                raise DBInvalidVbidError(vbid)
                
            return data
            
        except DBAPIError:
            raise
        except Exception as e:
            raise DBAPIError(f"Unexpected error resolving vbid: {str(e)}")
    
    def get_connections(self, from_station_id: str, to_station_id: str, 
                       departure_time: str, traveller_payload: List[Dict],
                       deutschland_ticket: bool = False) -> Dict:
        """
        Get connections between stations
        Enhanced with validation and error handling
        """
        # Validate station IDs (basic validation)
        if not from_station_id or not to_station_id:
            raise DBInvalidStationError("Empty station ID provided")
        
        payload = {
            'abfahrtsHalt': from_station_id,
            'ankunftsHalt': to_station_id,
            'anfrageZeitpunkt': departure_time,
            'ankunftSuche': 'ABFAHRT',
            'klasse': 'KLASSE_2',
            'reisende': traveller_payload,
            'produktgattungen': [
                product for product, enabled in self.config.products.items() 
                if enabled
            ],
            'schnelleVerbindungen': True,
            'deutschlandTicketVorhanden': deutschland_ticket
        }
        
        try:
            data = self._make_request('POST', '/angebote/fahrplan', json=payload)
            
            if not data.get("verbindungen"):
                raise DBConnectionNotFoundError(from_station_id, to_station_id)
                
            return data
            
        except DBAPIError:
            raise
        except Exception as e:
            raise DBAPIError(f"Unexpected error getting connections: {str(e)}")
```

### 3. Enhanced CLI Error Handling

**Current State**: Basic error handling with system exit.

**Recommended Enhancement** in `main.py`:

```python
def main():
    """Enhanced main function with structured error handling"""
    try:
        args = parser.parse_args()
        
        # Create API client with configuration
        config = DBAPIConfig()
        client = DBAPIClient(config)
        
        # Create traveller payload
        traveller_payload = create_traveller_payload(args.age, args.bahncard)
        
        # Process URL and find split tickets
        result = find_split_tickets_enhanced(client, args, traveller_payload)
        
        if result:
            display_results(result)
        else:
            print("❌ Keine Split-Ticket-Analyse möglich.")
            sys.exit(1)
            
    except DBConnectionNotFoundError as e:
        print(f"❌ Keine Verbindungen gefunden: {e}")
        print("💡 Tipp: Überprüfen Sie die URL und versuchen Sie es später erneut.")
        sys.exit(1)
        
    except DBInvalidVbidError as e:
        print(f"❌ Ungültige URL: {e}")
        print("💡 Tipp: Verwenden Sie eine aktuelle URL von bahn.de")
        sys.exit(1)
        
    except DBRateLimitError as e:
        print(f"⚠️  Rate Limit erreicht: {e}")
        if e.retry_after:
            print(f"💡 Bitte warten Sie {e.retry_after} Sekunden und versuchen Sie es erneut.")
        sys.exit(1)
        
    except DBAPIError as e:
        if e.is_server_error:
            print(f"⚠️  Server-Fehler (bitte später versuchen): {e}")
        else:
            print(f"❌ API-Fehler: {e}")
        
        if e.context:
            print(f"📋 Details: {e.context}")
        sys.exit(1)
        
    except Exception as e:
        print(f"💥 Unerwarteter Fehler: {e}")
        print("🐛 Bitte melden Sie diesen Fehler auf GitHub.")
        sys.exit(1)
```

## Priority 2: Medium-term Improvements

### 1. Configuration Management

Create `better_bahn/config.py`:

```python
"""
Configuration management following hafas-client patterns
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Optional
import json

@dataclass
class BetterBahnConfig:
    """Application-wide configuration"""
    
    # API Configuration
    api_config: DBAPIConfig = field(default_factory=DBAPIConfig)
    
    # CLI Configuration
    default_age: int = 30
    default_bahncard: Optional[str] = None
    default_deutschland_ticket: bool = False
    
    # Performance Configuration
    enable_caching: bool = True
    cache_ttl_minutes: int = 10
    parallel_requests: bool = False
    
    @classmethod
    def from_env(cls) -> 'BetterBahnConfig':
        """Load configuration from environment variables"""
        api_config = DBAPIConfig(
            rate_limit_delay=float(os.getenv('DB_RATE_LIMIT_DELAY', '0.5')),
            max_retries=int(os.getenv('DB_MAX_RETRIES', '3')),
            timeout=int(os.getenv('DB_TIMEOUT', '30'))
        )
        
        return cls(
            api_config=api_config,
            default_age=int(os.getenv('DEFAULT_AGE', '30')),
            enable_caching=os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'BetterBahnConfig':
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Parse and validate configuration
        # Implementation here
        pass
```

### 2. Caching Layer

Create `better_bahn/cache.py`:

```python
"""
Simple caching layer for API responses
"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl_seconds

class APICache:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, default_ttl: int = 600):  # 10 minutes
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry.data
        elif entry:
            # Remove expired entry
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache a value with TTL"""
        ttl = ttl or self.default_ttl
        self._cache[key] = CacheEntry(
            data=value,
            timestamp=time.time(),
            ttl_seconds=ttl
        )
    
    def clear(self) -> None:
        """Clear all cached entries"""
        self._cache.clear()
```

## Priority 3: Long-term Improvements

### 1. Comprehensive Testing

Create `tests/test_db_api_client.py`:

```python
"""
Test suite for DB API client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from better_bahn.db_api_client import DBAPIClient, DBAPIConfig
from better_bahn.errors import (
    DBNetworkError, DBRateLimitError, DBConnectionNotFoundError
)

class TestDBAPIClient:
    
    @pytest.fixture
    def client(self):
        """Create test client with short delays"""
        config = DBAPIConfig(rate_limit_delay=0.1, max_retries=2)
        return DBAPIClient(config)
    
    def test_successful_vbid_resolution(self, client):
        """Test successful vbid resolution"""
        mock_response = {
            "hinfahrtRecon": "test_recon_string",
            "startOrt": "Berlin Hbf",
            "zielOrt": "München Hbf"
        }
        
        with patch.object(client.session, 'request') as mock_request:
            mock_request.return_value.raise_for_status.return_value = None
            mock_request.return_value.json.return_value = mock_response
            
            result = client.resolve_vbid("test-vbid")
            assert result["hinfahrtRecon"] == "test_recon_string"
    
    def test_rate_limiting_retry(self, client):
        """Test rate limiting with automatic retry"""
        # Mock 429 response followed by success
        responses = [
            Mock(status_code=429),
            Mock(status_code=200)
        ]
        responses[0].raise_for_status.side_effect = requests.exceptions.HTTPError(response=responses[0])
        responses[1].raise_for_status.return_value = None
        responses[1].json.return_value = {"success": True}
        
        with patch.object(client.session, 'request', side_effect=responses):
            result = client.resolve_vbid("test-vbid")
            assert result["success"] is True
    
    def test_invalid_vbid_error(self, client):
        """Test invalid vbid handling"""
        mock_response = {"error": "vbid not found"}
        
        with patch.object(client.session, 'request') as mock_request:
            mock_request.return_value.raise_for_status.return_value = None
            mock_request.return_value.json.return_value = mock_response
            
            with pytest.raises(DBInvalidVbidError):
                client.resolve_vbid("invalid-vbid")
```

## Migration Strategy

### Phase 1 (Week 1-2): Foundation
1. ✅ Create error hierarchy in `better_bahn/errors.py`
2. ✅ Implement basic `DBAPIClient` class
3. ✅ Update main.py to use new error handling
4. ✅ Add basic configuration management

### Phase 2 (Week 3-4): Enhancement
1. Add caching layer
2. Implement comprehensive testing
3. Add request/response logging
4. Create detailed documentation

### Phase 3 (Week 5-6): Polish
1. Add monitoring and metrics
2. Performance optimization
3. Advanced rate limiting
4. Flutter app integration

## Expected Benefits

1. **Improved Reliability**: Structured error handling reduces silent failures
2. **Better User Experience**: Clear error messages with actionable guidance
3. **Easier Maintenance**: Modular architecture simplifies debugging and updates
4. **Performance Gains**: Caching and optimized rate limiting reduce API calls
5. **Future-Proofing**: Flexible configuration supports changing requirements

## Conclusion

These recommendations, inspired by hafas-client's mature patterns, will significantly improve Better-Bahn's robustness, maintainability, and user experience while maintaining the existing functionality and performance characteristics.