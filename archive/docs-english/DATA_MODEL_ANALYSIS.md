# Unified Data Model: hafas-client Alignment Analysis

This document defines Better-Bahn's unified data model with explicit alignment to hafas-client standards and naming conventions, while maintaining compatibility with Deutsche Bahn's API responses.

## Executive Summary

Better-Bahn adopts a hybrid approach that aligns with hafas-client naming conventions for consistency with public transport standards, while maintaining seamless integration with Deutsche Bahn's specific API response format.

## Data Structure Comparison

### Core Entities Mapping

| Entity Type | hafas-client | Better-Bahn Current | Better-Bahn Unified | Alignment Decision |
|-------------|-------------|---------------------|-------------------|-------------------|
| **Journey** | `Journey` | `verbindung` (raw dict) | `Connection` | ✅ **Align** - Use semantic English naming |
| **Leg** | `Leg` | `teilstrecke` (raw dict) | `ConnectionSegment` | ✅ **Align** - Clear segment semantics |
| **Stop** | `Stop` | `bahnhof` (raw dict) | `Station` | ✅ **Align** - Standard stop/station concept |
| **Line** | `Line` | `linie` (raw dict) | `TransportLine` | ✅ **Align** - Clear transport line semantics |
| **Location** | `Location` | Mixed/ad-hoc | `Location` | ✅ **Align** - Geographic location standard |
| **Product** | `Product` | `produktgattung` (raw) | `TransportMode` | ↗️ **Adapt** - Better semantic clarity |

## Detailed Entity Definitions

### 1. Location Entity

**hafas-client Reference:**
```javascript
{
  type: 'location',
  id: '8011160',
  name: 'Berlin Hbf',
  latitude: 52.525589,
  longitude: 13.369548
}
```

**Better-Bahn Current (DB API Response):**
```json
{
  "evaId": "8011160",
  "name": "Berlin Hbf",
  "coordinate": {
    "latitude": 52.525589,
    "longitude": 13.369548
  }
}
```

**Better-Bahn Unified Model:**
```python
@dataclass
class Location:
    """Geographic location following hafas-client standard"""
    id: str                    # Mapped from evaId
    name: str                  # Direct mapping
    latitude: Optional[float]  # Mapped from coordinate.latitude
    longitude: Optional[float] # Mapped from coordinate.longitude
    type: str = "station"      # Enhanced: station, poi, address
    
    @classmethod
    def from_db_api(cls, api_data: Dict) -> 'Location':
        """Parse from DB API response format"""
        coord = api_data.get('coordinate', {})
        return cls(
            id=api_data['evaId'],
            name=api_data['name'],
            latitude=coord.get('latitude'),
            longitude=coord.get('longitude'),
            type='station'
        )
```

### 2. Station Entity (Enhanced Stop)

**hafas-client Reference:**
```javascript
{
  type: 'stop',
  id: '8011160', 
  name: 'Berlin Hbf',
  location: { latitude: 52.525589, longitude: 13.369548 },
  departure: '2024-03-15T08:30:00+01:00',
  platform: '12'
}
```

**Better-Bahn Current:**
```json
{
  "bahnhof": {
    "evaId": "8011160",
    "name": "Berlin Hbf"
  },
  "abfahrtszeit": "2024-03-15T08:30:00+01:00",
  "gleis": "12"
}
```

**Better-Bahn Unified Model:**
```python
@dataclass
class Station:
    """Station with timing and platform information"""
    location: Location
    departure: Optional[datetime] = None    # Mapped from abfahrtszeit
    arrival: Optional[datetime] = None      # Mapped from ankunftszeit  
    platform: Optional[str] = None         # Mapped from gleis
    delay: Optional[int] = None             # Real-time delay in seconds
    cancelled: bool = False                 # Real-time cancellation status
    
    @classmethod
    def from_db_api(cls, api_data: Dict) -> 'Station':
        """Parse from DB API response format"""
        location = Location.from_db_api(api_data['bahnhof'])
        
        departure = None
        if 'abfahrtszeit' in api_data:
            departure = datetime.fromisoformat(api_data['abfahrtszeit'])
            
        arrival = None  
        if 'ankunftszeit' in api_data:
            arrival = datetime.fromisoformat(api_data['ankunftszeit'])
            
        return cls(
            location=location,
            departure=departure,
            arrival=arrival,
            platform=api_data.get('gleis'),
            delay=api_data.get('delay', 0),
            cancelled=api_data.get('cancelled', False)
        )
```

### 3. ConnectionSegment Entity (Leg)

**hafas-client Reference:**
```javascript
{
  origin: { id: '8011160', name: 'Berlin Hbf' },
  destination: { id: '8000261', name: 'München Hbf' },
  departure: '2024-03-15T08:30:00+01:00',
  arrival: '2024-03-15T12:45:00+01:00',
  line: { type: 'line', name: 'ICE 507' },
  mode: 'train'
}
```

**Better-Bahn Current:**
```json
{
  "startBahnhof": {"evaId": "8011160", "name": "Berlin Hbf"},
  "zielBahnhof": {"evaId": "8000261", "name": "München Hbf"},
  "abfahrt": "2024-03-15T08:30:00+01:00",
  "ankunft": "2024-03-15T12:45:00+01:00",
  "zugnummer": "ICE 507",
  "verkehrsmittel": "ICE"
}
```

**Better-Bahn Unified Model:**
```python
@dataclass
class ConnectionSegment:
    """Single segment of a journey (aligned with hafas-client Leg)"""
    origin: Station                        # Mapped from startBahnhof
    destination: Station                   # Mapped from zielBahnhof  
    line: Optional['TransportLine'] = None # Mapped from zugnummer
    duration: Optional[int] = None         # Calculated from departure/arrival
    distance: Optional[int] = None         # From DB API if available
    mode: str = "train"                    # Mapped from verkehrsmittel
    
    @property
    def departure(self) -> Optional[datetime]:
        """Convenience property for departure time"""
        return self.origin.departure
        
    @property  
    def arrival(self) -> Optional[datetime]:
        """Convenience property for arrival time"""
        return self.destination.arrival
    
    @classmethod
    def from_db_api(cls, api_data: Dict) -> 'ConnectionSegment':
        """Parse from DB API response format"""
        origin = Station.from_db_api({
            'bahnhof': api_data['startBahnhof'],
            'abfahrtszeit': api_data['abfahrt']
        })
        
        destination = Station.from_db_api({
            'bahnhof': api_data['zielBahnhof'], 
            'ankunftszeit': api_data['ankunft']
        })
        
        # Calculate duration
        duration = None
        if origin.departure and destination.arrival:
            duration = int((destination.arrival - origin.departure).total_seconds())
        
        return cls(
            origin=origin,
            destination=destination,
            line=TransportLine.from_db_api(api_data),
            duration=duration,
            mode=_map_transport_mode(api_data.get('verkehrsmittel', 'train'))
        )
```

### 4. Connection Entity (Journey)

**hafas-client Reference:**
```javascript
{
  type: 'journey',
  legs: [...],
  duration: 15900000,  // milliseconds
  price: { amount: 89.90, currency: 'EUR' }
}
```

**Better-Bahn Current:**
```json
{
  "verbindung": {
    "teilstrecken": [...],
    "dauer": 15900,
    "preis": 89.90,
    "waehrung": "EUR"
  }
}
```

**Better-Bahn Unified Model:**
```python
@dataclass  
class Connection:
    """Complete journey with pricing (aligned with hafas-client Journey)"""
    segments: List[ConnectionSegment]       # Mapped from teilstrecken
    price: Optional[float] = None          # Mapped from preis
    currency: str = "EUR"                  # Mapped from waehrung
    duration: Optional[int] = None         # Mapped from dauer (seconds)
    departure: Optional[datetime] = None   # From first segment
    arrival: Optional[datetime] = None     # From last segment  
    transfers: int = 0                     # Calculated from segments
    is_deutschland_ticket_eligible: bool = False
    
    @property
    def departure(self) -> Optional[datetime]:
        """Journey departure time from first segment"""
        return self.segments[0].departure if self.segments else None
        
    @property
    def arrival(self) -> Optional[datetime]:  
        """Journey arrival time from last segment"""
        return self.segments[-1].arrival if self.segments else None
        
    @property
    def transfers(self) -> int:
        """Number of transfers (segments - 1)"""
        return max(0, len(self.segments) - 1)
    
    @classmethod
    def from_db_api(cls, api_data: Dict) -> 'Connection':
        """Parse from DB API response format"""
        segments = [
            ConnectionSegment.from_db_api(segment_data) 
            for segment_data in api_data.get('teilstrecken', [])
        ]
        
        return cls(
            segments=segments,
            price=api_data.get('preis'),
            currency=api_data.get('waehrung', 'EUR'),
            duration=api_data.get('dauer'),
            is_deutschland_ticket_eligible=api_data.get('deutschlandTicketGueltig', False)
        )
```

### 5. TransportLine Entity

**hafas-client Reference:**
```javascript
{
  type: 'line',
  name: 'ICE 507', 
  mode: 'train',
  product: 'nationalExpress'
}
```

**Better-Bahn Current:**
```json
{
  "zugnummer": "ICE 507",
  "verkehrsmittel": "ICE",
  "gattung": "FERNVERKEHR"
}
```

**Better-Bahn Unified Model:**
```python
@dataclass
class TransportLine:
    """Transport line information (aligned with hafas-client Line)"""
    name: str                       # Mapped from zugnummer
    mode: str = "train"            # Mapped from verkehrsmittel  
    product: str = "train"         # Mapped from gattung
    operator: Optional[str] = None # DB for Deutsche Bahn services
    
    @classmethod
    def from_db_api(cls, api_data: Dict) -> 'TransportLine':
        """Parse from DB API response format"""
        return cls(
            name=api_data.get('zugnummer', ''),
            mode=_map_transport_mode(api_data.get('verkehrsmittel', 'train')),
            product=_map_transport_product(api_data.get('gattung', 'train')),
            operator='DB'
        )
```

## Transport Mode and Product Mapping

### Mode Mapping (hafas-client compatible)

| DB API Value | hafas-client Mode | Better-Bahn Mode | Description |
|--------------|------------------|------------------|-------------|
| `ICE` | `train` | `train` | High-speed rail |
| `IC` | `train` | `train` | Intercity rail |
| `RE` | `train` | `train` | Regional express |
| `RB` | `train` | `train` | Regional rail |
| `S` | `train` | `suburban` | S-Bahn suburban rail |
| `BUS` | `bus` | `bus` | Bus service |
| `TRAM` | `tram` | `tram` | Tram/streetcar |
| `U` | `subway` | `subway` | U-Bahn subway |

### Product Mapping

| DB API Gattung | hafas-client Product | Better-Bahn Product |
|---------------|---------------------|-------------------|
| `FERNVERKEHR` | `nationalExpress` | `long_distance` |
| `NAHVERKEHR` | `regional` | `regional` |
| `STADTVERKEHR` | `suburban` | `urban` |
| `BUS` | `bus` | `bus` |

```python
def _map_transport_mode(db_mode: str) -> str:
    """Map DB API transport mode to hafas-client compatible mode"""
    mode_mapping = {
        'ICE': 'train',
        'IC': 'train', 
        'EC': 'train',
        'RE': 'train',
        'RB': 'train',
        'S': 'suburban',
        'BUS': 'bus',
        'TRAM': 'tram',
        'U': 'subway'
    }
    return mode_mapping.get(db_mode.upper(), 'train')

def _map_transport_product(db_gattung: str) -> str:
    """Map DB API product category to hafas-client compatible product"""
    product_mapping = {
        'FERNVERKEHR': 'long_distance',
        'NAHVERKEHR': 'regional', 
        'STADTVERKEHR': 'urban',
        'BUS': 'bus'
    }
    return product_mapping.get(db_gattung.upper(), 'train')
```

## Data Model Usage Examples

### Creating a Connection from DB API Response

```python
# DB API response
db_response = {
    "verbindung": {
        "teilstrecken": [
            {
                "startBahnhof": {"evaId": "8011160", "name": "Berlin Hbf"},
                "zielBahnhof": {"evaId": "8000261", "name": "München Hbf"},
                "abfahrt": "2024-03-15T08:30:00+01:00", 
                "ankunft": "2024-03-15T12:45:00+01:00",
                "zugnummer": "ICE 507",
                "verkehrsmittel": "ICE"
            }
        ],
        "preis": 89.90,
        "dauer": 15900
    }
}

# Parse to unified model
connection = Connection.from_db_api(db_response["verbindung"])

# hafas-client compatible access patterns
print(f"Journey from {connection.segments[0].origin.location.name}")
print(f"to {connection.segments[-1].destination.location.name}")
print(f"Duration: {connection.duration} seconds")
print(f"Transfers: {connection.transfers}")
print(f"Price: {connection.price} {connection.currency}")
```

### Flutter/Dart Model Alignment

```dart
// Corresponding Dart models for Flutter app
class Location {
  final String id;
  final String name;
  final double? latitude;
  final double? longitude;
  final String type;
  
  const Location({
    required this.id,
    required this.name,
    this.latitude,
    this.longitude,
    this.type = 'station',
  });
  
  factory Location.fromDbApi(Map<String, dynamic> json) {
    final coord = json['coordinate'] as Map<String, dynamic>?;
    return Location(
      id: json['evaId'],
      name: json['name'],
      latitude: coord?['latitude']?.toDouble(),
      longitude: coord?['longitude']?.toDouble(),
    );
  }
}

class Connection {
  final List<ConnectionSegment> segments;
  final double? price;
  final String currency;
  final int? duration;
  final bool isDeutschlandTicketEligible;
  
  // Implementation follows same patterns as Python version
}
```

## Alignment Benefits

### 1. **Consistency with Standards**
- Follows established public transport data conventions
- Enables potential interoperability with other hafas-client tools
- Provides familiar API for developers from other transit projects

### 2. **Clear Semantic Naming**
- English naming improves international developer accessibility  
- Semantic clarity (Connection vs verbindung, Station vs bahnhof)
- Consistent naming patterns across entities

### 3. **Type Safety and Validation**
- Strong typing with dataclasses/type hints
- Clear property definitions and constraints
- Validated data transformations from API responses

### 4. **Backward Compatibility**
- Maintains compatibility with existing DB API responses
- Gradual migration path from current ad-hoc structures
- Clear mapping between old and new data models

### 5. **Cross-Platform Consistency**  
- Aligned naming between Python CLI and Flutter app
- Consistent developer experience across platforms
- Shared mental models for data structures

## Implementation Migration Path

### Phase 1: Foundation
1. ✅ **Define unified models** with hafas-client alignment
2. ✅ **Create mapping functions** from DB API responses  
3. ✅ **Add comprehensive type hints** and validation
4. ✅ **Document alignment decisions** and rationale

### Phase 2: Integration  
1. **Update main.py** to use unified models internally
2. **Migrate Flutter app** to aligned Dart models
3. **Create adapter functions** for backward compatibility
4. **Add comprehensive testing** for data transformations

### Phase 3: Optimization
1. **Performance optimization** for data transformations
2. **Caching integration** with unified models
3. **Real-time data integration** using consistent structures
4. **API response validation** against unified schemas

This unified data model provides Better-Bahn with hafas-client compatibility while maintaining seamless integration with Deutsche Bahn's specific API responses and existing German user interface elements.