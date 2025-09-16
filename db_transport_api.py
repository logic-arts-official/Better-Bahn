"""
v6.db.transport.rest API Client for Better-Bahn

Enhanced API client with comprehensive rate limiting, caching, metrics,
and graceful degradation features.

API Documentation: https://v6.db.transport.rest/api.html
"""

import requests
import time
import logging
from typing import Optional, Dict, List, Any, Union
from urllib.parse import quote
from dataclasses import dataclass

from better_bahn_config import BetterBahnConfig, APIConfig
from better_bahn_cache import CacheManager
from better_bahn_metrics import MetricsCollector, PerformanceTimer


@dataclass
class Location:
    """Represents a station location"""
    id: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Create Location from API response"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )


@dataclass
class APIError(Exception):
    """Represents an API error with additional context"""
    message: str
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None
    is_rate_limited: bool = False
    is_server_error: bool = False
    retry_after: Optional[int] = None


class DBTransportAPIClient:
    """Enhanced client for v6.db.transport.rest API"""
    
    def __init__(self, config: Optional[BetterBahnConfig] = None):
        """
        Initialize the API client with full configuration support.
        
        Args:
            config: Configuration object (uses default if None)
        """
        if config is None:
            from better_bahn_config import default_config
            config = default_config
        
        self.config = config.api
        self.cache_manager = CacheManager(config.cache) if config.cache.enable_memory_cache or config.cache.enable_disk_cache else None
        self.metrics = MetricsCollector(config.logging) if config.logging.enable_metrics else None
        self.logger = logging.getLogger('better_bahn.api_client')
        
        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json'
        })
        
        self.logger.info(f"DB Transport API client initialized (base_url: {self.config.base_url})")
    
    def _make_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a cache key for the request"""
        return {
            'endpoint': endpoint,
            'params': params or {}
        }
    
    def _parse_retry_after(self, response: requests.Response) -> Optional[int]:
        """Parse Retry-After header from response"""
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        return None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                      use_cache: bool = True, cache_ttl: Optional[int] = None) -> Optional[Dict]:
        """
        Make API request with comprehensive error handling, caching, and metrics.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_cache: Whether to use caching
            cache_ttl: Custom cache TTL (uses default if None)
            
        Returns:
            API response as dictionary or None on error
        """
        
        # Check feature flag
        if not self.config.enable_realtime:
            self.logger.debug("Real-time API disabled by feature flag")
            return None
        
        # Create cache key
        cache_key = self._make_cache_key(endpoint, params)
        
        # Try cache first
        if use_cache and self.cache_manager:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                if self.metrics:
                    self.metrics.record_request(
                        url=f"{self.config.base_url}{endpoint}",
                        cache_hit=True,
                        cache_source=cached_result['metadata']['source']
                    )
                
                self.logger.debug(f"Cache hit for {endpoint} from {cached_result['metadata']['source']}")
                return cached_result['data']
        
        # Make HTTP request with retries
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                with PerformanceTimer(self.metrics, url) as timer:
                    # Apply rate limiting
                    if attempt == 0:
                        time.sleep(self.config.rate_limit_delay)
                    
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.config.timeout
                    )
                    
                    # Record metrics
                    if self.metrics:
                        self.metrics.record_request(
                            url=url,
                            status_code=response.status_code,
                            latency_ms=timer.latency_ms,
                            cache_hit=False
                        )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Cache successful response
                    if use_cache and self.cache_manager:
                        self.cache_manager.set(cache_key, result, cache_ttl, cache_ttl)
                    
                    self.logger.debug(f"API request successful: {endpoint} ({timer.latency_ms:.1f}ms)")
                    return result
                    
            except requests.exceptions.HTTPError as e:
                response = e.response
                
                # Record error metrics
                if self.metrics:
                    self.metrics.record_request(
                        url=url,
                        status_code=response.status_code,
                        latency_ms=timer.latency_ms if 'timer' in locals() else 0,
                        cache_hit=False,
                        error=f"HTTP {response.status_code}"
                    )
                
                if response.status_code == 429:  # Rate limited
                    retry_after = self._parse_retry_after(response)
                    
                    if self.config.respect_retry_after and retry_after:
                        wait_time = min(retry_after, self.config.max_backoff_delay)
                        self.logger.warning(f"Rate limited, waiting {wait_time}s (Retry-After header)")
                        time.sleep(wait_time)
                    elif self.config.exponential_backoff:
                        wait_time = min(
                            (2 ** attempt) * self.config.rate_limit_delay,
                            self.config.max_backoff_delay
                        )
                        self.logger.warning(f"Rate limited, exponential backoff: {wait_time:.1f}s")
                        time.sleep(wait_time)
                    else:
                        time.sleep(self.config.rate_limit_delay)
                    
                    continue  # Retry
                
                elif response.status_code >= 500:  # Server error
                    if attempt == self.config.max_retries - 1:
                        self.logger.error(f"Server error {response.status_code} for {endpoint} (final attempt)")
                        break
                    else:
                        wait_time = min(1.0 * (2 ** attempt), 10.0)  # Up to 10 seconds
                        self.logger.warning(f"Server error {response.status_code}, retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                
                else:  # Client error (4xx)
                    self.logger.error(f"Client error {response.status_code} for {endpoint}: {response.text}")
                    break
                    
            except requests.RequestException as e:
                # Record error metrics
                if self.metrics:
                    self.metrics.record_request(
                        url=url,
                        latency_ms=timer.latency_ms if 'timer' in locals() else 0,
                        cache_hit=False,
                        error=type(e).__name__
                    )
                
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"Request failed for {endpoint} (final attempt): {e}")
                else:
                    wait_time = min(1.0 * (2 ** attempt), 5.0)
                    self.logger.warning(f"Request failed for {endpoint}, retrying in {wait_time:.1f}s: {e}")
                    time.sleep(wait_time)
                    continue
        
        # All attempts failed - try stale cache as fallback
        if use_cache and self.cache_manager:
            stale_result = self.cache_manager.get(cache_key, use_stale=True)
            if stale_result:
                self.logger.warning(f"Using stale cache data for {endpoint}")
                
                if self.metrics:
                    self.metrics.record_request(
                        url=url,
                        cache_hit=True,
                        cache_source=f"stale_{stale_result['metadata']['source']}"
                    )
                
                return stale_result['data']
        
        self.logger.error(f"All attempts failed for {endpoint}")
        return None
    
    def find_locations(self, query: str, results: int = 5) -> Optional[List[Location]]:
        """
        Find stations by name or location.
        
        Args:
            query: Search query (station name)
            results: Maximum number of results (default: 5)
            
        Returns:
            List of Location objects or None on error
        """
        params = {
            'query': query,
            'results': results
        }
        
        response = self._make_request('/locations', params, cache_ttl=300)  # Cache for 5 minutes
        
        if response:
            try:
                return [Location.from_dict(loc) for loc in response if loc.get('type') == 'station']
            except (KeyError, TypeError) as e:
                self.logger.error(f"Failed to parse locations response: {e}")
                return None
        
        return None
    
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
        # Cache journey data for 2 minutes (real-time data changes frequently)
        response = self._make_request('/journeys', params, cache_ttl=120)
        return response
    
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
        endpoint = f"/stops/{quote(station_id)}/departures"
        params = {
            'duration': duration,
            'results': results
        }
        
        if when:
            params['when'] = when
            
        return self._make_request(endpoint, params)
    
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
        endpoint = f"/trips/{quote(trip_id)}"
        params = {}
        
        if line_name:
            params['lineName'] = line_name
            
        return self._make_request(endpoint, params)
    
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
    
    def is_available(self) -> bool:
        """
        Check if the API is available.
        
        Returns:
            True if API is responding, False otherwise
        """
        try:
            # Simple test request with minimal cache
            result = self._make_request('/', use_cache=False)
            return result is not None
        except Exception:
            return False
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics"""
        if self.cache_manager:
            return self.cache_manager.get_stats()
        return None
    
    def get_metrics(self, window_minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Get performance metrics"""
        if self.metrics:
            return self.metrics.get_comprehensive_stats(window_minutes)
        return None
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        if self.cache_manager:
            self.cache_manager.clear()
            self.logger.info("API client cache cleared")
    
    def cleanup_cache(self) -> Dict[str, int]:
        """Cleanup expired cache entries"""
        if self.cache_manager:
            return self.cache_manager.cleanup()
        return {}


def get_real_time_journey_info(from_station: str, to_station: str, 
                              config: Optional[BetterBahnConfig] = None) -> Optional[Dict[str, Any]]:
    """
    High-level function to get real-time journey information.
    
    Args:
        from_station: Origin station name
        to_station: Destination station name
        config: Configuration (uses default if None)
        
    Returns:
        Dictionary with journey information and real-time status
    """
    client = DBTransportAPIClient(config)
    
    try:
        # Get journey data
        journeys_data = client.get_journeys(from_station, to_station)
        
        if not journeys_data or not journeys_data.get('journeys'):
            return {
                'available': False,
                'error': 'No journeys found',
                'journeys': [],
                'journeys_count': 0
            }
        
        # Process journey data for real-time information
        processed_journeys = []
        
        for journey in journeys_data['journeys']:
            real_time_status = client.get_real_time_status(journey)
            processed_journey = {
                'duration_minutes': journey.get('duration', 0) // 60 if journey.get('duration') else 0,
                'transfers': len(journey.get('legs', [])) - 1 if journey.get('legs') else 0,
                'real_time_status': {
                    'has_delays': real_time_status['has_delays'],
                    'total_delay_minutes': real_time_status['total_delay_minutes'],
                    'has_cancellations': real_time_status['cancelled_legs'] > 0,
                    'status': 'disrupted' if (real_time_status['has_delays'] or real_time_status['cancelled_legs'] > 0) else 'on_time'
                }
            }
            processed_journeys.append(processed_journey)
        
        return {
            'available': True,
            'journeys': processed_journeys,
            'journeys_count': len(processed_journeys),
            'from_station': from_station,
            'to_station': to_station
        }
        
    except Exception as e:
        client.logger.error(f"Failed to get real-time journey info: {e}")
        return {
            'available': False,
            'error': str(e),
            'journeys': [],
            'journeys_count': 0
        }


def test_api_client():
    """Test function to verify API client functionality."""
    print("Testing DB Transport API Client...")
    
    client = DBTransportAPIClient()
    
    # Test location search
    print("\n1. Testing location search for 'Berlin Hbf'...")
    locations = client.find_locations("Berlin Hbf", results=1)
    if locations and len(locations) > 0:
        berlin_id = locations[0]['id']
        print(f"   Found: {locations[0]['name']} (ID: {berlin_id})")
    else:
        print("   Failed to find Berlin Hbf")
        return
    
    # Test journey search
    print("\n2. Testing journey search Berlin -> München...")
    journeys = client.get_journeys(berlin_id, "8000261", results=1)  # München Hbf
    if journeys and 'journeys' in journeys and len(journeys['journeys']) > 0:
        journey = journeys['journeys'][0]
        print(f"   Found journey with {len(journey['legs'])} legs")
        
        # Test real-time status
        status = client.get_real_time_status(journey)
        print(f"   Real-time status: {status['has_delays']} delays, {status['total_delay_minutes']} min total")
    else:
        print("   Failed to find journeys")
    
    print("\nAPI client test completed!")


if __name__ == "__main__":
    test_api_client()