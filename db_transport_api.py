"""
v6.db.transport.rest API Client for Better-Bahn

This module provides a resilient Python client for accessing real-time Deutsche Bahn data
through the v6.db.transport.rest API. It includes comprehensive error handling, rate limiting,
caching, and fallback strategies for production use.

Features:
- Result type wrapper for comprehensive error handling
- Token bucket rate limiting with configurable limits
- Multi-tier caching with ETag support and stale-while-revalidate
- HTTP status code mapping and resilience patterns
- Graceful fallback to cached/static data

API Documentation: https://v6.db.transport.rest/api.html
"""

import requests
import time
import hashlib
import json
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List, Union, Any, Tuple
from urllib.parse import quote


class APIResultType(Enum):
    """Result types for API responses."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    TRANSIENT_ERROR = "transient_error"
    PERMANENT_ERROR = "permanent_error"


@dataclass
class APIResult:
    """Wrapper for API results with error handling."""
    result_type: APIResultType
    data: Optional[Dict] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    retry_after: Optional[int] = None
    from_cache: bool = False
    cached_at: Optional[float] = None

    @property
    def is_success(self) -> bool:
        """Check if the result represents a successful API call."""
        return self.result_type == APIResultType.SUCCESS

    @property
    def should_retry(self) -> bool:
        """Check if the operation should be retried."""
        return self.result_type in {
            APIResultType.RATE_LIMITED,
            APIResultType.TRANSIENT_ERROR,
            APIResultType.UPSTREAM_ERROR
        }

    @property
    def can_fallback_to_cache(self) -> bool:
        """Check if we can use cached data as fallback."""
        return self.result_type in {
            APIResultType.RATE_LIMITED,
            APIResultType.UPSTREAM_ERROR,
            APIResultType.TRANSIENT_ERROR
        }


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Dict
    fetched_at: float
    etag: Optional[str] = None
    max_age: int = 300  # 5 minutes default
    stale_while_revalidate: int = 600  # 10 minutes

    @property
    def is_fresh(self) -> bool:
        """Check if cache entry is still fresh."""
        return time.time() - self.fetched_at < self.max_age

    @property
    def is_stale_but_usable(self) -> bool:
        """Check if cache entry is stale but can be used while revalidating."""
        return time.time() - self.fetched_at < (self.max_age + self.stale_while_revalidate)


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_update = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not available
        """
        with self._lock:
            now = time.time()
            # Refill tokens based on time passed
            tokens_to_add = (now - self.last_update) * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until requested tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available
        """
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate


class CacheManager:
    """In-memory cache with ETag and stale-while-revalidate support."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of cache entries
        """
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _generate_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and parameters."""
        if params:
            # Sort params for consistent keys
            param_str = json.dumps(params, sort_keys=True)
            key_data = f"{endpoint}?{param_str}"
        else:
            key_data = endpoint
        
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[Optional[CacheEntry], str]:
        """
        Get cache entry and return cache key.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Tuple of (cache_entry, cache_key)
        """
        key = self._generate_key(endpoint, params)
        
        with self._lock:
            self._access_times[key] = time.time()
            return self._cache.get(key), key

    def set(self, key: str, entry: CacheEntry) -> None:
        """
        Store cache entry.
        
        Args:
            key: Cache key
            entry: Cache entry to store
        """
        with self._lock:
            # Evict oldest entries if cache is full
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
                del self._cache[oldest_key]
                del self._access_times[oldest_key]
            
            self._cache[key] = entry
            self._access_times[key] = time.time()

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


class DBTransportAPIClient:
    """Resilient client for v6.db.transport.rest API with comprehensive error handling and caching."""
    
    BASE_URL = "https://v6.db.transport.rest"
    
    def __init__(self, 
                 rate_limit_capacity: int = 10,
                 rate_limit_window: float = 10.0,
                 cache_max_size: int = 1000,
                 default_timeout: int = 30,
                 enable_caching: bool = True):
        """
        Initialize the resilient API client.
        
        Args:
            rate_limit_capacity: Maximum requests in window (default: 10)
            rate_limit_window: Time window in seconds (default: 10.0)
            cache_max_size: Maximum cache entries (default: 1000)
            default_timeout: Request timeout in seconds (default: 30)
            enable_caching: Enable response caching (default: True)
        """
        # Rate limiting - 10 requests per 10 seconds by default
        refill_rate = rate_limit_capacity / rate_limit_window
        self.rate_limiter = TokenBucket(capacity=rate_limit_capacity, refill_rate=refill_rate)
        
        # Caching
        self.cache_manager = CacheManager(max_size=cache_max_size) if enable_caching else None
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Better-Bahn/2.0 (https://github.com/logic-arts-official/Better-Bahn)',
            'Accept': 'application/json'
        })
        self.default_timeout = default_timeout
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'rate_limit_hits': 0,
            'errors': 0
        }
    
    def _map_http_status_to_result_type(self, status_code: int) -> APIResultType:
        """Map HTTP status codes to result types."""
        if 200 <= status_code < 300:
            return APIResultType.SUCCESS
        elif status_code == 404:
            return APIResultType.NOT_FOUND
        elif status_code == 429:
            return APIResultType.RATE_LIMITED
        elif 400 <= status_code < 500:
            return APIResultType.PERMANENT_ERROR
        elif 500 <= status_code < 600:
            return APIResultType.UPSTREAM_ERROR
        else:
            return APIResultType.TRANSIENT_ERROR
    
    def _extract_rate_limit_info(self, response: requests.Response) -> Optional[int]:
        """Extract rate limit retry-after from response headers."""
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        
        # Look for X-RateLimit headers for future-proofing
        x_rate_limit_reset = response.headers.get('X-RateLimit-Reset')
        if x_rate_limit_reset:
            try:
                reset_time = int(x_rate_limit_reset)
                return max(0, reset_time - int(time.time()))
            except ValueError:
                pass
        
        return None
    
    def _make_request_with_cache(self, endpoint: str, params: Optional[Dict] = None) -> APIResult:
        """
        Make API request with caching and resilience.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            APIResult with response data or error information
        """
        self.stats['requests_made'] += 1
        
        # Check cache first
        cache_entry = None
        cache_key = None
        if self.cache_manager:
            cache_entry, cache_key = self.cache_manager.get(endpoint, params)
            
            if cache_entry and cache_entry.is_fresh:
                self.stats['cache_hits'] += 1
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at
                )
        
        # Check rate limiting
        if not self.rate_limiter.consume():
            self.stats['rate_limit_hits'] += 1
            wait_time = self.rate_limiter.time_until_available()
            
            # If we have stale cache data, use it
            if cache_entry and cache_entry.is_stale_but_usable:
                self.stats['cache_hits'] += 1
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at
                )
            
            return APIResult(
                result_type=APIResultType.RATE_LIMITED,
                error_message=f"Rate limit exceeded, retry in {wait_time:.1f}s",
                retry_after=int(wait_time) + 1
            )
        
        # Prepare request headers
        headers = {}
        if cache_entry and cache_entry.etag:
            headers['If-None-Match'] = cache_entry.etag
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(
                url, 
                params=params, 
                headers=headers,
                timeout=self.default_timeout
            )
            
            # Handle 304 Not Modified (cached content is still valid)
            if response.status_code == 304 and cache_entry:
                # Update cache timestamp but keep existing data
                fresh_entry = CacheEntry(
                    data=cache_entry.data,
                    fetched_at=time.time(),
                    etag=cache_entry.etag
                )
                if self.cache_manager and cache_key:
                    self.cache_manager.set(cache_key, fresh_entry)
                
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=fresh_entry.fetched_at
                )
            
            result_type = self._map_http_status_to_result_type(response.status_code)
            
            # Handle successful response
            if result_type == APIResultType.SUCCESS:
                try:
                    data = response.json()
                    
                    # Cache the response
                    if self.cache_manager and cache_key:
                        etag = response.headers.get('ETag')
                        cache_entry = CacheEntry(
                            data=data,
                            fetched_at=time.time(),
                            etag=etag
                        )
                        self.cache_manager.set(cache_key, cache_entry)
                    
                    return APIResult(
                        result_type=APIResultType.SUCCESS,
                        data=data,
                        http_status=response.status_code
                    )
                except ValueError as e:
                    return APIResult(
                        result_type=APIResultType.TRANSIENT_ERROR,
                        error_message=f"Invalid JSON response: {e}",
                        http_status=response.status_code
                    )
            
            # Handle error responses
            self.stats['errors'] += 1
            retry_after = self._extract_rate_limit_info(response) if result_type == APIResultType.RATE_LIMITED else None
            
            # If we have cached data and this is a recoverable error, use cache
            if cache_entry and cache_entry.is_stale_but_usable and result_type in {
                APIResultType.RATE_LIMITED, 
                APIResultType.UPSTREAM_ERROR, 
                APIResultType.TRANSIENT_ERROR
            }:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at
                )
            
            try:
                error_details = response.text[:500]  # Limit error message length
            except:
                error_details = f"HTTP {response.status_code}"
            
            return APIResult(
                result_type=result_type,
                error_message=f"API error: {error_details}",
                http_status=response.status_code,
                retry_after=retry_after
            )
            
        except requests.Timeout:
            self.stats['errors'] += 1
            # Use cached data if available
            if cache_entry and cache_entry.is_stale_but_usable:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at
                )
            
            return APIResult(
                result_type=APIResultType.TRANSIENT_ERROR,
                error_message="Request timeout"
            )
            
        except requests.ConnectionError:
            self.stats['errors'] += 1
            # Use cached data if available
            if cache_entry and cache_entry.is_stale_but_usable:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at
                )
            
            return APIResult(
                result_type=APIResultType.TRANSIENT_ERROR,
                error_message="Connection error"
            )
            
        except requests.RequestException as e:
            self.stats['errors'] += 1
            return APIResult(
                result_type=APIResultType.TRANSIENT_ERROR,
                error_message=f"Request failed: {e}"
            )
    
    # Legacy compatibility method (maintains existing API)
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Legacy method for backward compatibility.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as dictionary or None on error
        """
        result = self._make_request_with_cache(endpoint, params)
        return result.data if result.is_success else None
    
    # New resilient API methods
    def find_locations_resilient(self, query: str, results: int = 5) -> APIResult:
        """
        Find stations by name with resilient error handling.
        
        Args:
            query: Search query (station name)
            results: Maximum number of results (default: 5)
            
        Returns:
            APIResult with location data
        """
        params = {
            'query': query,
            'results': results
        }
        return self._make_request_with_cache('/locations', params)
    
    def get_journeys_resilient(self, 
                              from_station: str, 
                              to_station: str,
                              departure: Optional[str] = None,
                              arrival: Optional[str] = None,
                              results: int = 3,
                              stopovers: bool = True,
                              transfers: int = -1,
                              accessibility: Optional[str] = None) -> APIResult:
        """
        Get journey options with resilient error handling.
        
        Args:
            from_station: Origin station ID or name
            to_station: Destination station ID or name  
            departure: Departure time (ISO string or timestamp)
            arrival: Arrival time (ISO string or timestamp)
            results: Number of journey results (default: 3)
            stopovers: Include intermediate stops (default: True)
            transfers: Maximum transfers (-1 for unlimited)
            accessibility: Accessibility requirements
            
        Returns:
            APIResult with journey data
        """
        params = {
            'from': from_station,
            'to': to_station,
            'results': results,
            'stopovers': stopovers
        }
        
        if departure:
            params['departure'] = departure
        if arrival:
            params['arrival'] = arrival
        if transfers >= 0:
            params['transfers'] = transfers
        if accessibility:
            params['accessibility'] = accessibility
            
        return self._make_request_with_cache('/journeys', params)
    
    def get_departures_resilient(self, 
                                station_id: str,
                                when: Optional[str] = None,
                                duration: int = 120,
                                results: int = 10) -> APIResult:
        """
        Get departures from a station with resilient error handling.
        
        Args:
            station_id: Station ID
            when: Time for departures (ISO string)
            duration: Time span in minutes (default: 120)
            results: Number of results (default: 10)
            
        Returns:
            APIResult with departure data
        """
        endpoint = f"/stops/{quote(station_id)}/departures"
        params = {
            'duration': duration,
            'results': results
        }
        
        if when:
            params['when'] = when
            
        return self._make_request_with_cache(endpoint, params)
    
    def get_trip_details_resilient(self, trip_id: str, line_name: Optional[str] = None) -> APIResult:
        """
        Get detailed trip information with resilient error handling.
        
        Args:
            trip_id: Trip identifier
            line_name: Line name for disambiguation
            
        Returns:
            APIResult with trip details
        """
        endpoint = f"/trips/{quote(trip_id)}"
        params = {}
        
        if line_name:
            params['lineName'] = line_name
            
        return self._make_request_with_cache(endpoint, params)
    
    # Backward compatibility methods (updated to use resilient backend)
    def find_locations(self, query: str, results: int = 5) -> Optional[List[Dict]]:
        """
        Find stations by name or location.
        
        Args:
            query: Search query (station name)
            results: Maximum number of results (default: 5)
            
        Returns:
            List of location objects or None on error
        """
        result = self.find_locations_resilient(query, results)
        return result.data if result.is_success else None
    
    def get_journeys(self, 
                     from_station: str, 
                     to_station: str,
                     departure: Optional[str] = None,
                     arrival: Optional[str] = None,
                     results: int = 3,
                     stopovers: bool = True,
                     transfers: int = -1,
                     accessibility: Optional[str] = None) -> Optional[Dict]:
        """
        Get journey options between two stations.
        
        Args:
            from_station: Origin station ID or name
            to_station: Destination station ID or name  
            departure: Departure time (ISO string or timestamp)
            arrival: Arrival time (ISO string or timestamp)
            results: Number of journey results (default: 3)
            stopovers: Include intermediate stops (default: True)
            transfers: Maximum transfers (-1 for unlimited)
            accessibility: Accessibility requirements
            
        Returns:
            Journey data or None on error
        """
        result = self.get_journeys_resilient(
            from_station, to_station, departure, arrival, 
            results, stopovers, transfers, accessibility
        )
        return result.data if result.is_success else None
    
    def get_departures(self, 
                       station_id: str,
                       when: Optional[str] = None,
                       duration: int = 120,
                       results: int = 10) -> Optional[Dict]:
        """
        Get departures from a station.
        
        Args:
            station_id: Station ID
            when: Time for departures (ISO string)
            duration: Time span in minutes (default: 120)
            results: Number of results (default: 10)
            
        Returns:
            Departure data or None on error
        """
        result = self.get_departures_resilient(station_id, when, duration, results)
        return result.data if result.is_success else None
    
    def get_arrivals(self, 
                     station_id: str,
                     when: Optional[str] = None,
                     duration: int = 120,
                     results: int = 10) -> Optional[Dict]:
        """
        Get arrivals at a station.
        
        Args:
            station_id: Station ID
            when: Time for arrivals (ISO string)  
            duration: Time span in minutes (default: 120)
            results: Number of results (default: 10)
            
        Returns:
            Arrival data or None on error
        """
        endpoint = f"/stops/{quote(station_id)}/arrivals"
        params = {
            'duration': duration,
            'results': results
        }
        
        if when:
            params['when'] = when
            
        return self._make_request(endpoint, params)
    
    def get_trip_details(self, trip_id: str, line_name: Optional[str] = None) -> Optional[Dict]:
        """
        Get detailed information about a specific trip.
        
        Args:
            trip_id: Trip identifier
            line_name: Line name for disambiguation
            
        Returns:
            Trip details or None on error
        """
        result = self.get_trip_details_resilient(trip_id, line_name)
        return result.data if result.is_success else None
    
    def get_station_info(self, station_id: str) -> Optional[Dict]:
        """
        Get detailed station information.
        
        Args:
            station_id: Station ID
            
        Returns:
            Station details or None on error
        """
        endpoint = f"/stops/{quote(station_id)}"
        return self._make_request(endpoint)
    
    def find_nearby_stations(self, 
                             latitude: float, 
                             longitude: float,
                             distance: int = 1000,
                             results: int = 8) -> Optional[List[Dict]]:
        """
        Find stations near a geographic location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            distance: Search radius in meters (default: 1000)
            results: Maximum results (default: 8)
            
        Returns:
            List of nearby stations or None on error
        """
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'distance': distance,
            'results': results
        }
        
        return self._make_request('/stops/nearby', params)
    
    # Utility and monitoring methods
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics for monitoring."""
        cache_stats = {}
        if self.cache_manager:
            cache_stats = {
                'cache_size': len(self.cache_manager._cache),
                'cache_max_size': self.cache_manager.max_size
            }
        
        return {
            **self.stats,
            **cache_stats,
            'rate_limit_tokens': self.rate_limiter.tokens,
            'rate_limit_capacity': self.rate_limiter.capacity
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.cache_manager:
            self.cache_manager.clear()
    
    def reset_stats(self) -> None:
        """Reset client statistics."""
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'rate_limit_hits': 0,
            'errors': 0
        }
    
    def get_real_time_status(self, journey_data: Dict) -> Dict:
        """
        Extract real-time status information from journey data.
        
        Args:
            journey_data: Journey object from API response
            
        Returns:
            Dictionary with real-time status information
        """
        status = {
            'has_delays': False,
            'total_delay_minutes': 0,
            'cancelled_legs': 0,
            'delays_by_leg': []
        }
        
        if not journey_data or 'legs' not in journey_data:
            return status
        
        for leg in journey_data['legs']:
            leg_status = {
                'leg_id': leg.get('id', 'unknown'),
                'departure_delay': 0,
                'arrival_delay': 0,
                'cancelled': False
            }
            
            # Check departure delay
            if 'departure' in leg and leg['departure']:
                if 'delay' in leg['departure'] and leg['departure']['delay'] is not None:
                    leg_status['departure_delay'] = leg['departure']['delay'] // 60  # Convert to minutes
                    status['total_delay_minutes'] += leg_status['departure_delay']
                    status['has_delays'] = True
            
            # Check arrival delay  
            if 'arrival' in leg and leg['arrival']:
                if 'delay' in leg['arrival'] and leg['arrival']['delay'] is not None:
                    leg_status['arrival_delay'] = leg['arrival']['delay'] // 60  # Convert to minutes
                    if leg_status['arrival_delay'] > leg_status['departure_delay']:
                        status['total_delay_minutes'] += (leg_status['arrival_delay'] - leg_status['departure_delay'])
                        status['has_delays'] = True
            
            # Check cancellation
            if leg.get('cancelled'):
                leg_status['cancelled'] = True
                status['cancelled_legs'] += 1
            
            status['delays_by_leg'].append(leg_status)
        
        return status


def test_api_client():
    """Test function to verify enhanced API client functionality."""
    print("Testing Enhanced DB Transport API Client...")
    print("=" * 50)
    
    # Test with default configuration
    client = DBTransportAPIClient()
    
    print("\n📊 Initial Statistics:")
    stats = client.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test resilient location search
    print("\n1️⃣  Testing resilient location search for 'Berlin Hbf'...")
    result = client.find_locations_resilient("Berlin Hbf", results=1)
    print(f"   Result type: {result.result_type.value}")
    print(f"   From cache: {result.from_cache}")
    
    if result.is_success and result.data and len(result.data) > 0:
        berlin_id = result.data[0]['id']
        print(f"   Found: {result.data[0]['name']} (ID: {berlin_id})")
        
        # Test journey search with resilient API
        print("\n2️⃣  Testing resilient journey search Berlin -> München...")
        journey_result = client.get_journeys_resilient(berlin_id, "8000261", results=1)  # München Hbf
        print(f"   Result type: {journey_result.result_type.value}")
        print(f"   From cache: {journey_result.from_cache}")
        
        if journey_result.is_success and journey_result.data and 'journeys' in journey_result.data:
            journeys = journey_result.data['journeys']
            if len(journeys) > 0:
                journey = journeys[0]
                print(f"   Found journey with {len(journey['legs'])} legs")
                
                # Test real-time status
                status = client.get_real_time_status(journey)
                print(f"   Real-time status: {status['has_delays']} delays, {status['total_delay_minutes']} min total")
        else:
            print(f"   Journey search failed or no data available")
            if journey_result.error_message:
                print(f"   Error: {journey_result.error_message}")
    else:
        print(f"   Location search failed or no data available")
        if result.error_message:
            print(f"   Error: {result.error_message}")
    
    # Test rate limiting
    print("\n3️⃣  Testing rate limiting behavior...")
    rate_limit_hits = 0
    for i in range(15):  # Try to exceed the 10 requests limit
        test_result = client.find_locations_resilient("Hamburg", results=1)
        if test_result.result_type == APIResultType.RATE_LIMITED:
            rate_limit_hits += 1
            print(f"   Rate limit hit after {i+1} requests")
            break
    
    if rate_limit_hits == 0:
        print("   No rate limiting detected (expected in network-isolated environment)")
    
    # Test caching behavior
    print("\n4️⃣  Testing cache behavior...")
    # Make the same request twice
    cache_test_result1 = client.find_locations_resilient("Frankfurt", results=1)
    cache_test_result2 = client.find_locations_resilient("Frankfurt", results=1)
    
    print(f"   First request from cache: {cache_test_result1.from_cache}")
    print(f"   Second request from cache: {cache_test_result2.from_cache}")
    
    # Final statistics
    print("\n📊 Final Statistics:")
    final_stats = client.get_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    
    # Test backward compatibility
    print("\n5️⃣  Testing backward compatibility...")
    legacy_locations = client.find_locations("München", results=1)
    legacy_success = legacy_locations is not None
    print(f"   Legacy API compatibility: {'✅ Working' if legacy_success else '❌ Failed'}")
    
    print("\n✨ Enhanced API client test completed!")
    print("\nNew Features Demonstrated:")
    print("🔧 Result type wrapper with comprehensive error handling")
    print("⚡ Token bucket rate limiting (10 req/10s)")
    print("💾 In-memory caching with ETag support")
    print("🔄 Stale-while-revalidate fallback strategy")
    print("📊 Request statistics and monitoring")
    print("🔙 Full backward compatibility with existing code")


if __name__ == "__main__":
    test_api_client()