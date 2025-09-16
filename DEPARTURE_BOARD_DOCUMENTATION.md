# Departure Board Integration - Static + Real-time Documentation

## Overview

The Better-Bahn departure board integration provides comprehensive departure information by combining static timetable data with real-time information from the v6.db.transport.rest API. This implements the requested "Integration Flow (Static + Realtime)" functionality.

## Features

### Core Functionality
- **Static Schedule Loading**: Baseline planned departure times from timetable data
- **Real-time Data Integration**: Live departure information with delays and cancellations
- **Smart Matching**: Matches static and real-time data using trip IDs and heuristics
- **Status Computation**: Automatically calculates delays and determines status
- **Platform Change Detection**: Identifies and highlights platform changes

### Data Model

The departure board uses a composite model with the following fields:

#### DepartureBoardEntry
- `planned_departure`: Static timetable departure time
- `realtime_departure`: Live departure time (if available)
- `delay_minutes`: Computed delay in minutes
- `status`: One of ON_TIME, DELAYED, CANCELLED, UNKNOWN
- `line`: Train line name (e.g., "ICE 123", "RB 45")
- `destination`: Final destination
- `planned_platform`: Static platform assignment
- `realtime_platform`: Live platform information
- `platform_changed`: Boolean indicating platform changes
- `message`: Service messages or disruption information

#### Status Values
- **ON_TIME**: Departure is on schedule (0 minutes delay)
- **DELAYED**: Departure is delayed (> 0 minutes)
- **CANCELLED**: Service is cancelled
- **UNKNOWN**: Status cannot be determined

## Usage

### Command Line Interface

#### Standalone CLI (departure_board_cli.py)
```bash
# Show departure board for a station
python departure_board_cli.py "Berlin Hbf"

# Show departures with custom parameters
python departure_board_cli.py "8011160" --duration 180 --results 25

# Filter delayed trains only
python departure_board_cli.py "Berlin Hbf" --delayed-only --min-delay 5

# Filter by status
python departure_board_cli.py "Berlin Hbf" --status DELAYED

# Demo mode with sample data
python departure_board_cli.py "Berlin Hbf" --demo
```

#### Integrated with main.py
```bash
# Show departure board from main Better-Bahn CLI
python main.py --departure-board --station "Berlin Hbf"

# Demo mode
python main.py --departure-board --demo

# With station search
python main.py --departure-board --station "München"
```

### Programmatic Usage

```python
from departure_board import DepartureBoardService, DepartureStatus

# Initialize service
service = DepartureBoardService()

# Create departure board for a station
board = service.create_departure_board(
    station_id="8011160",  # Berlin Hbf
    duration=120,          # Next 2 hours
    results=20             # Up to 20 departures
)

# Filter departures
delayed = board.get_delayed_departures(min_delay_minutes=5)
cancelled = board.get_departures_by_status(DepartureStatus.CANCELLED)

# Format for display
formatted = service.format_departure_board(board)
print(formatted)
```

### Demo Mode

The system includes a demo mode that works without internet connectivity:

```python
# Create demo data
board = service.create_demo_departure_board("Berlin Hbf")
```

Demo mode provides realistic sample data including:
- On-time departures
- Various delay scenarios (3-15 minutes)
- Platform changes
- Cancellations with replacement service messages
- Different train types (ICE, IC, RE, RB, S-Bahn)

## Technical Implementation

### Data Integration Flow

1. **Station Resolution**: Convert station names to EVA numbers using location search
2. **Static Data Loading**: Load baseline timetable data from YAML schema
3. **Real-time Fetch**: Retrieve live departure data from v6.db.transport.rest API
4. **Data Matching**: Match static and real-time entries using:
   - Trip ID (primary)
   - Line name + planned time + stop ID (fallback heuristic)
5. **Status Computation**: Calculate delays and determine status
6. **Platform Analysis**: Detect platform changes
7. **Message Aggregation**: Collect service messages and disruption info

### Error Handling

The system implements robust error handling for:
- Network connectivity issues
- Malformed API responses
- Missing data fields
- Invalid time formats
- Station not found scenarios

### Rate Limiting

Complies with API rate limiting requirements:
- 200ms delay between requests
- Graceful degradation when API unavailable
- Fallback to demo mode for testing

## Integration Benefits

### For Users
- **Complete Picture**: See both planned and actual departure times
- **Real-time Updates**: Live delay and cancellation information
- **Platform Alerts**: Immediate notification of platform changes
- **Service Messages**: Important disruption and replacement service info

### For Developers
- **Modular Design**: Separate CLI and library components
- **Extensible**: Easy to add new filters and display options
- **Testable**: Demo mode allows testing without API access
- **Well-Documented**: Comprehensive type hints and docstrings

## Example Output

```
🚂 Departure Board - Berlin Hbf
📅 Last updated: 12:09:29
================================================================================
    Time  Delay         Line Destination               Platform Status
--------------------------------------------------------------------------------
   12:14 On time     ICE 1601 Hamburg-Altona                  12 ✅ ON_TIME
   12:21    +8'      IC 2083 Dresden Hbf                     8* ⚠️ DELAYED
   12:27 On time         RE 3 Stralsund Hbf                   14 ✅ ON_TIME
   12:34   +15'     ICE 1078 München Hbf                      3 ⚠️ DELAYED
   12:41   CANC        RB 25 Oranienburg                     16 ❌ CANCELLED
   12:47    +3'           S3 Erkner                          S3 ⚠️ DELAYED
   12:54 On time      ICE 373 Paris Est                        1 ✅ ON_TIME
   13:01 On time         RE 1 Brandenburg Hbf                 12 ✅ ON_TIME
--------------------------------------------------------------------------------
📊 Summary: 4 on time, 3 delayed, 1 cancelled
* Platform changed
```

## Future Enhancements

- **Arrival Boards**: Similar functionality for arrivals
- **Multi-Station**: Compare departures across multiple stations
- **Historical Data**: Track delay patterns over time
- **Mobile Integration**: Flutter app integration
- **Push Notifications**: Real-time alerts for specific trains
- **Journey Planning**: Integration with existing split-ticket analysis

## Compliance and Standards

- **Deutsche Bahn API**: Uses official schema definitions from Timetables v1.0.213
- **EVA Numbers**: Validates 7-digit EVA station numbers
- **Rate Limiting**: Respects API usage guidelines
- **Error Handling**: Graceful degradation and user-friendly messages
- **Data Privacy**: No personal data storage or transmission