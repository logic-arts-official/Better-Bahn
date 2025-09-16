"""
Departure Board Integration - Static + Real-time Data

This module implements a departure board system that combines static timetable data
with real-time information from v6.db.transport.rest API to provide comprehensive
departure information with delays, cancellations, and platform changes.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import yaml
import os
from db_transport_api import DBTransportAPIClient


class DepartureStatus(Enum):
    """Status of a departure."""
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass
class DepartureBoardEntry:
    """
    A single entry in the departure board combining static and real-time data.
    """
    # Basic trip information
    line: str                           # Line name (e.g., "ICE 123", "RB 45")
    destination: str                    # Final destination
    trip_id: Optional[str] = None       # Trip identifier for matching
    
    # Time information
    planned_departure: Optional[datetime] = None    # Static timetable departure time
    realtime_departure: Optional[datetime] = None   # Real-time departure time
    delay_minutes: int = 0                          # Computed delay in minutes
    
    # Status information
    status: DepartureStatus = DepartureStatus.UNKNOWN
    
    # Platform information
    planned_platform: Optional[str] = None
    realtime_platform: Optional[str] = None
    platform_changed: bool = False
    
    # Additional information
    message: Optional[str] = None       # Service message or disruption info
    operator: Optional[str] = None      # Transport operator
    
    def update_delay(self):
        """Calculate and update delay based on planned vs real-time departure."""
        if self.planned_departure and self.realtime_departure:
            delta = self.realtime_departure - self.planned_departure
            self.delay_minutes = int(delta.total_seconds() / 60)
            
            # Update status based on delay
            if self.delay_minutes == 0:
                self.status = DepartureStatus.ON_TIME
            elif self.delay_minutes > 0:
                self.status = DepartureStatus.DELAYED
        elif self.realtime_departure is None and self.planned_departure:
            # No real-time data might indicate cancellation or unknown status
            self.status = DepartureStatus.UNKNOWN
    
    def update_platform_change(self):
        """Check and update platform change status."""
        if (self.planned_platform and self.realtime_platform and 
            self.planned_platform != self.realtime_platform):
            self.platform_changed = True


@dataclass
class DepartureBoard:
    """
    Complete departure board for a station.
    """
    station_name: str
    station_id: str
    last_updated: datetime
    departures: List[DepartureBoardEntry]
    
    def get_departures_by_status(self, status: DepartureStatus) -> List[DepartureBoardEntry]:
        """Get all departures with a specific status."""
        return [dep for dep in self.departures if dep.status == status]
    
    def get_delayed_departures(self, min_delay_minutes: int = 1) -> List[DepartureBoardEntry]:
        """Get all departures with delays greater than specified minutes."""
        return [dep for dep in self.departures 
                if dep.status == DepartureStatus.DELAYED and dep.delay_minutes >= min_delay_minutes]


class DepartureBoardService:
    """
    Service for creating and managing departure boards with static + real-time integration.
    """
    
    def __init__(self):
        """Initialize the departure board service."""
        self.api_client = DBTransportAPIClient()
        self.static_data = self._load_static_timetable_data()
    
    def _load_static_timetable_data(self) -> Optional[Dict]:
        """Load static timetable data from YAML file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "data", "Timetables-1.0.213.yaml")
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"⚠️ Warning: Could not load static timetable data: {e}")
            return None
    
    def create_departure_board(self, 
                               station_id: str, 
                               when: Optional[str] = None,
                               duration: int = 120, 
                               results: int = 20) -> Optional[DepartureBoard]:
        """
        Create a complete departure board for a station combining static and real-time data.
        
        Args:
            station_id: Station ID (EVA number)
            when: Time for departures (ISO string, defaults to now)
            duration: Time span in minutes (default: 120)
            results: Number of results (default: 20)
            
        Returns:
            Complete departure board or None on error
        """
        try:
            # Get station information
            station_info = self.api_client.get_station_info(station_id)
            if not station_info:
                print(f"Could not get station info for {station_id}")
                return None
            
            station_name = station_info.get('name', station_id)
            
            # Get real-time departures
            departures_data = self.api_client.get_departures(
                station_id=station_id,
                when=when,
                duration=duration,
                results=results
            )
            
            if not departures_data or 'departures' not in departures_data:
                print(f"No departure data found for station {station_name}")
                return None
            
            # Process departures and create entries
            departure_entries = []
            for dep_data in departures_data['departures']:
                entry = self._create_departure_entry(dep_data, station_id)
                if entry:
                    departure_entries.append(entry)
            
            # Sort by planned departure time
            departure_entries.sort(key=lambda x: x.planned_departure or datetime.min)
            
            return DepartureBoard(
                station_name=station_name,
                station_id=station_id,
                last_updated=datetime.now(),
                departures=departure_entries
            )
            
        except Exception as e:
            print(f"Error creating departure board for {station_id}: {e}")
            return None
    
    def _create_departure_entry(self, departure_data: Dict, station_id: str) -> Optional[DepartureBoardEntry]:
        """
        Create a departure board entry from API data.
        
        Args:
            departure_data: Departure data from API
            station_id: Station ID for context
            
        Returns:
            DepartureBoardEntry or None if data insufficient
        """
        try:
            # Validate input data
            if not departure_data or not isinstance(departure_data, dict):
                return None
            
            # Extract basic information with robust null checking
            line_info = departure_data.get('line', {})
            if not isinstance(line_info, dict):
                line_info = {}
            
            line_name = line_info.get('name', 'Unknown')
            
            # Handle destination which might be None in sandboxed environments
            destination_info = departure_data.get('destination')
            if isinstance(destination_info, dict):
                destination = destination_info.get('name', 'Unknown')
            else:
                destination = 'Unknown'
            
            trip_id = departure_data.get('tripId')
            
            # Extract time information
            planned_when = departure_data.get('plannedWhen')
            when = departure_data.get('when')  # real-time departure
            delay = departure_data.get('delay')  # delay in seconds
            
            # Parse times
            planned_departure = None
            realtime_departure = None
            
            if planned_when:
                try:
                    planned_departure = datetime.fromisoformat(planned_when.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # Fallback for invalid time format
                    planned_departure = None
            
            if when:
                try:
                    realtime_departure = datetime.fromisoformat(when.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    realtime_departure = None
            elif planned_departure and delay is not None:
                try:
                    # Calculate real-time from planned + delay
                    realtime_departure = planned_departure + timedelta(seconds=delay)
                except (TypeError, ValueError):
                    realtime_departure = None
            
            # Extract platform information
            planned_platform = departure_data.get('plannedPlatform')
            realtime_platform = departure_data.get('platform')
            
            # Determine cancellation status
            cancelled = departure_data.get('cancelled', False)
            
            # Get operator information safely
            operator_info = line_info.get('operator')
            operator_name = None
            if isinstance(operator_info, dict):
                operator_name = operator_info.get('name')
            
            # Create the entry
            entry = DepartureBoardEntry(
                line=line_name,
                destination=destination,
                trip_id=trip_id,
                planned_departure=planned_departure,
                realtime_departure=realtime_departure,
                planned_platform=planned_platform,
                realtime_platform=realtime_platform,
                operator=operator_name
            )
            
            # Set status based on data
            if cancelled:
                entry.status = DepartureStatus.CANCELLED
            else:
                entry.update_delay()
            
            # Check for platform changes
            entry.update_platform_change()
            
            # Add any additional messages
            remarks = departure_data.get('remarks', [])
            if isinstance(remarks, list):
                messages = []
                for remark in remarks:
                    if isinstance(remark, dict) and remark.get('text'):
                        messages.append(remark['text'])
                if messages:
                    entry.message = '; '.join(messages)
            
            return entry
            
        except Exception as e:
            # More specific error logging for debugging
            print(f"Error creating departure entry from data: {e}")
            if departure_data:
                print(f"Data keys: {list(departure_data.keys()) if isinstance(departure_data, dict) else 'Not a dict'}")
            return None
    
    def create_demo_departure_board(self, station_name: str = "Berlin Hbf") -> DepartureBoard:
        """
        Create a demo departure board with sample data for testing and demonstration.
        
        Args:
            station_name: Name of the station for the demo board
            
        Returns:
            Sample departure board with realistic data
        """
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Sample departure data
        sample_departures = [
            {
                'line': 'ICE 1601',
                'destination': 'Hamburg-Altona',
                'planned_minutes': 5,
                'delay_minutes': 0,
                'platform': '12',
                'status': DepartureStatus.ON_TIME
            },
            {
                'line': 'IC 2083',
                'destination': 'Dresden Hbf',
                'planned_minutes': 12,
                'delay_minutes': 8,
                'platform': '6',
                'platform_changed': '8',
                'status': DepartureStatus.DELAYED,
                'message': 'Technische Störung am Fahrzeug'
            },
            {
                'line': 'RE 3',
                'destination': 'Stralsund Hbf',
                'planned_minutes': 18,
                'delay_minutes': 0,
                'platform': '14',
                'status': DepartureStatus.ON_TIME
            },
            {
                'line': 'ICE 1078',
                'destination': 'München Hbf',
                'planned_minutes': 25,
                'delay_minutes': 15,
                'platform': '3',
                'status': DepartureStatus.DELAYED,
                'message': 'Verspätung aus vorheriger Fahrt'
            },
            {
                'line': 'RB 25',
                'destination': 'Oranienburg',
                'planned_minutes': 32,
                'delay_minutes': -1,
                'platform': '16',
                'status': DepartureStatus.CANCELLED,
                'message': 'Zug fällt aus - Ersatzverkehr mit Bussen'
            },
            {
                'line': 'S3',
                'destination': 'Erkner',
                'planned_minutes': 38,
                'delay_minutes': 3,
                'platform': 'S3',
                'status': DepartureStatus.DELAYED
            },
            {
                'line': 'ICE 373',
                'destination': 'Paris Est',
                'planned_minutes': 45,
                'delay_minutes': 0,
                'platform': '1',
                'status': DepartureStatus.ON_TIME
            },
            {
                'line': 'RE 1',
                'destination': 'Brandenburg Hbf',
                'planned_minutes': 52,
                'delay_minutes': 0,
                'platform': '12',
                'status': DepartureStatus.ON_TIME
            }
        ]
        
        # Create departure entries
        entries = []
        for dep_data in sample_departures:
            planned_time = now + timedelta(minutes=dep_data['planned_minutes'])
            realtime_time = None
            
            if dep_data['status'] != DepartureStatus.CANCELLED:
                realtime_time = planned_time + timedelta(minutes=dep_data['delay_minutes'])
            
            entry = DepartureBoardEntry(
                line=dep_data['line'],
                destination=dep_data['destination'],
                trip_id=f"trip_{dep_data['line'].replace(' ', '_')}",
                planned_departure=planned_time,
                realtime_departure=realtime_time,
                delay_minutes=dep_data['delay_minutes'],
                status=dep_data['status'],
                planned_platform=dep_data['platform'],
                realtime_platform=dep_data.get('platform_changed', dep_data['platform']),
                message=dep_data.get('message'),
                operator="Deutsche Bahn AG"
            )
            
            entry.platform_changed = 'platform_changed' in dep_data
            entries.append(entry)
        
        return DepartureBoard(
            station_name=station_name,
            station_id="8011160",  # Berlin Hbf EVA
            last_updated=now,
            departures=entries
        )
        """
        Find station ID by name using the location search API.
        
        Args:
            station_name: Name of the station to search for
            
        Returns:
            Station information or None if not found
        """
        try:
            locations = self.api_client.find_locations(station_name, results=1)
            if locations and len(locations) > 0:
                location = locations[0]
                if location.get('type') == 'station':
                    return {
                        'id': location['id'],
                        'name': location['name'],
                        'location': location.get('location', {})
                    }
            return None
        except Exception as e:
            print(f"Error finding station {station_name}: {e}")
            return None
    
    def format_departure_board(self, board: DepartureBoard, max_entries: int = 10) -> str:
        """
        Format departure board for console output.
        
        Args:
            board: Departure board to format
            max_entries: Maximum number of entries to show
            
        Returns:
            Formatted string representation
        """
        if not board or not board.departures:
            return "No departures found."
        
        output = []
        output.append(f"🚂 Departure Board - {board.station_name}")
        output.append(f"📅 Last updated: {board.last_updated.strftime('%H:%M:%S')}")
        output.append("=" * 80)
        output.append(f"{'Time':>8} {'Delay':>6} {'Line':>12} {'Destination':<25} {'Platform':>8} {'Status'}")
        output.append("-" * 80)
        
        for i, dep in enumerate(board.departures[:max_entries]):
            # Format time
            time_str = dep.planned_departure.strftime('%H:%M') if dep.planned_departure else "??:??"
            
            # Format delay
            if dep.status == DepartureStatus.CANCELLED:
                delay_str = "CANC"
            elif dep.delay_minutes > 0:
                delay_str = f"+{dep.delay_minutes}'"
            elif dep.delay_minutes == 0:
                delay_str = "On time"
            else:
                delay_str = ""
            
            # Format platform
            platform = dep.realtime_platform or dep.planned_platform or "?"
            if dep.platform_changed:
                platform = f"{platform}*"
            
            # Status icon
            status_icon = {
                DepartureStatus.ON_TIME: "✅",
                DepartureStatus.DELAYED: "⚠️",
                DepartureStatus.CANCELLED: "❌",
                DepartureStatus.UNKNOWN: "❓"
            }.get(dep.status, "❓")
            
            output.append(
                f"{time_str:>8} {delay_str:>6} {dep.line:>12} {dep.destination[:25]:<25} "
                f"{platform:>8} {status_icon} {dep.status.value}"
            )
        
        if len(board.departures) > max_entries:
            output.append(f"... and {len(board.departures) - max_entries} more departures")
        
        # Summary statistics
        delayed = len(board.get_departures_by_status(DepartureStatus.DELAYED))
        cancelled = len(board.get_departures_by_status(DepartureStatus.CANCELLED))
        on_time = len(board.get_departures_by_status(DepartureStatus.ON_TIME))
        
        output.append("-" * 80)
        output.append(f"📊 Summary: {on_time} on time, {delayed} delayed, {cancelled} cancelled")
        output.append("* Platform changed")
        
        return "\n".join(output)