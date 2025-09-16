"""
v6.db.transport.rest API Client for Better-Bahn

This module provides a Python client for accessing real-time Deutsche Bahn data
through the v6.db.transport.rest API. It complements the existing bahn.de web API
with additional real-time features like live delays and journey updates.

API Documentation: https://v6.db.transport.rest/api.html
"""

import requests
import time
from typing import Optional, Dict, List
from urllib.parse import quote


class DBTransportAPIClient:
    """Client for v6.db.transport.rest API"""
    
    BASE_URL = "https://v6.db.transport.rest"
    
    def __init__(self, rate_limit_delay: float = 0.2):
        """
        Initialize the API client.
        
        Args:
            rate_limit_delay: Delay between requests in seconds (default: 0.2s)
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Better-Bahn/1.0 (https://github.com/logic-arts-official/Better-Bahn)',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as dictionary or None on error
        """
        time.sleep(self.rate_limit_delay)
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except (ValueError, TypeError) as e:
            # Handle JSON parsing errors
            print(f"DB Transport API JSON parsing failed: {e}")
            return None
        except requests.RequestException as e:
            print(f"DB Transport API request failed: {e}")
            return None
    
    def find_locations(self, query: str, results: int = 5) -> Optional[List[Dict]]:
        """
        Find stations by name or location.
        
        Args:
            query: Search query (station name)
            results: Maximum number of results (default: 5)
            
        Returns:
            List of location objects or None on error
        """
        params = {
            'query': query,
            'results': results
        }
        response = self._make_request('/locations', params)
        return response if response else None
    
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
            
        return self._make_request('/journeys', params)
    
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
                    if leg_status['departure_delay'] > 0:
                        status['has_delays'] = True
            
            # Check arrival delay  
            if 'arrival' in leg and leg['arrival']:
                if 'delay' in leg['arrival'] and leg['arrival']['delay'] is not None:
                    leg_status['arrival_delay'] = leg['arrival']['delay'] // 60  # Convert to minutes
                    if leg_status['arrival_delay'] > leg_status['departure_delay']:
                        additional_delay = leg_status['arrival_delay'] - leg_status['departure_delay']
                        status['total_delay_minutes'] += additional_delay
                        if additional_delay > 0:
                            status['has_delays'] = True
            
            # Check cancellation
            if leg.get('cancelled'):
                leg_status['cancelled'] = True
                status['cancelled_legs'] += 1
            
            status['delays_by_leg'].append(leg_status)
        
        return status


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