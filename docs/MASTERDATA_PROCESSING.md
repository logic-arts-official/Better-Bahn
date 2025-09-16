# Masterdata Processing Documentation

## Overview

Better-Bahn now includes comprehensive masterdata processing capabilities for Deutsche Bahn station and service data, with schema validation, normalization, and versioning features.

## Schema Definitions

### File: `data/masterdata_schema.json`

Defines JSON Schema structures for:

**Stations**:
- `id`: Unique station identifier
- `name`: Station name
- `name_normalized`: Normalized name for search (casefold + diacritics removal)
- `eva`: EVA station number (7-digit format)
- `lat`/`lon`: Coordinates
- `ds100`: DS100 station code
- `platforms`: Available platforms
- `external_ids`: External system identifiers
- `metadata`: Additional station information

**Services/Trips**:
- `id`: Unique service identifier
- `product`: Train product type (ICE, IC, RE, etc.)
- `stops`: Sequence of stops with station_id, timing, platform
- `operating_days`: Days when service operates
- `attributes`: Service features and capabilities

## Python Implementation

### Core Functions

#### Schema and Version Management
```python
load_masterdata_schema()        # Load JSON schema
load_timetables_version()       # Load version information
update_timetables_version(stats) # Update version with statistics
compute_file_hash(file_path)    # Compute SHA256 hash
```

#### Validation Functions
```python
validate_station_data(station)  # Validate station against schema
validate_service_data(service)  # Validate service against schema
validate_eva_number(eva_no)     # Validate EVA number format
```

#### Data Processing
```python
normalize_station_name(name)           # Normalize for search index
precompute_adjacency_data(stations, services) # Generate routing data
```

### Usage Examples

```python
import main

# Load and validate station data
station = {
    'id': 'MUC_HBF',
    'name': 'München Hauptbahnhof',
    'name_normalized': main.normalize_station_name('München Hauptbahnhof'),
    'eva': 8000261,
    'lat': 48.1400,
    'lon': 11.5583
}

is_valid, errors = main.validate_station_data(station)
if is_valid:
    print("Station data is valid!")
else:
    print(f"Validation errors: {errors}")

# Normalize station names for search
normalized = main.normalize_station_name("München Hauptbahnhof")
# Result: "munchen hauptbahnhof"
```

## Dart Implementation

### File: `flutter-app/lib/services/masterdata_validation.dart`

Provides Flutter-compatible validation services:

#### Data Classes
- `StationData`: Station information
- `ServiceData`: Service/trip information  
- `ServiceStop`: Individual stop within a service
- `ValidationResult`: Validation outcome with errors/warnings

#### Validation Functions
```dart
MasterdataValidationService.normalizeStationName(name)
MasterdataValidationService.validateEvaNumber(eva)
MasterdataValidationService.validateStationData(station)
MasterdataValidationService.validateServiceData(service)
```

#### Development Testing
```dart
await MasterdataValidationService.runDevValidation();
```

## Versioning System

### File: `data/timetables.version.json`

Tracks masterdata version and integrity:

```json
{
  "version": "1.0.213",
  "file_sha256": "computed_hash_of_timetables_file",
  "generated_at": "2024-01-01T00:00:00.000Z",
  "schema_version": "1.0.0",
  "source": {
    "api_version": "1.0.213",
    "api_base": "https://apis.deutschebahn.com/...",
    "description": "Deutsche Bahn Timetables API Schema"
  },
  "statistics": {
    "total_stations": 0,
    "total_services": 0,
    "last_updated": "2024-01-01T00:00:00.000Z"
  },
  "validation": {
    "schema_file": "data/masterdata_schema.json",
    "validation_enabled": true,
    "validation_errors": 0
  }
}
```

## Station Name Normalization

Converts station names to search-friendly format:

**Process**:
1. Unicode normalization (NFD decomposition)
2. Diacritical marks removal (ä→a, ö→o, ü→u, etc.)
3. Case folding (Unicode-aware lowercase)
4. Whitespace normalization

**Examples**:
- "München Hauptbahnhof" → "munchen hauptbahnhof"
- "Köln Hbf" → "koln hbf"
- "Düsseldorf Flughafen" → "dusseldorf flughafen"

## Adjacency Computation

Precomputes route connectivity for journey planning:

```python
routing_data = precompute_adjacency_data(stations, services)
```

**Output**:
- `adjacency`: Station-to-station connectivity graph
- `route_segments`: Direct connections with timing
- Metadata for routing algorithms

## Testing

### Python Tests
```bash
python test_masterdata.py
```

Comprehensive test suite covering:
- Schema loading and validation
- Station/service data validation
- Name normalization
- EVA number validation
- Adjacency computation
- Version management
- Hash computation

### Dart Tests
```bash
dart test_dart_validation.dart
```

Tests normalization and validation logic in Dart environment.

## Integration

### Dependencies

**Python**: Add to `pyproject.toml`:
```toml
dependencies = [
    "jsonschema>=4.10.0",
    # ... other dependencies
]
```

**Flutter**: Import validation service:
```dart
import 'package:better_bahn/services/masterdata_validation.dart';
```

### Error Handling

All validation functions return structured error information:
- Graceful fallback when jsonschema unavailable
- Detailed error messages for debugging
- Warnings for non-critical issues

## Future Enhancements

1. **Real-time Data Integration**: Merge static masterdata with live updates
2. **Caching Layer**: Performance optimization for repeated validations
3. **Additional Schemas**: Extend to cover pricing, disruptions, etc.
4. **API Integration**: Direct connection to Deutsche Bahn APIs
5. **ML Features**: Station similarity and recommendation algorithms

## Files Overview

```
data/
├── masterdata_schema.json      # JSON Schema definitions
├── timetables.version.json     # Version and integrity tracking
└── Timetables-1.0.213.yaml   # Original DB API schema

flutter-app/lib/services/
└── masterdata_validation.dart # Dart validation service

test_masterdata.py             # Python test suite
test_dart_validation.dart      # Dart test script
```

This masterdata processing system provides a solid foundation for reliable data handling in the Better-Bahn application.