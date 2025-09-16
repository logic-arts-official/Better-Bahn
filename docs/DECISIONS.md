# Architecture Decision Log (ADL)

This document records important architecture decisions made during Better-Bahn development, particularly those influenced by the hafas-client analysis.

## Decision Record Format

Each decision follows the format:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: Why this decision was needed
- **Decision**: What was decided
- **Consequences**: Expected outcomes and trade-offs

---

## ADR-001: hafas-client Pattern Adoption Strategy

**Status**: Accepted  
**Date**: 2024-09-16  
**Context**: 

After analyzing the mature `public-transport/hafas-client` project, we identified several beneficial patterns for improving Better-Bahn's architecture, reliability, and maintainability. The hafas-client provides excellent examples of API client design, error handling, and developer experience patterns.

**Decision**: 

We will selectively adopt hafas-client patterns according to the following priority framework:

### Phase 1: Immediate Adoption (✅ Adopt)
1. **Structured Error Handling**
   - Implement hierarchical error types (DBAPIError, DBNetworkError, etc.)
   - Add context information to errors for better debugging
   - Provide user-friendly error messages with actionable guidance

2. **Enhanced CLI Error Handling**  
   - Replace silent failures with explicit error reporting
   - Add helpful tips and troubleshooting information
   - Standardize error exit codes

3. **Basic Configuration Management**
   - Create configurable rate limiting and timeout settings
   - Support environment variable configuration
   - Implement flexible product filtering

### Phase 2: Medium-term Adoption (➡️ Consider)
1. **Request/Response Caching**
   - Implement simple in-memory caching for repeated queries
   - Configurable TTL for different endpoint types
   - Cache invalidation strategies

2. **Advanced Rate Limiting**
   - Exponential backoff for retries
   - Configurable throttling patterns
   - Rate limit detection and handling

3. **Comprehensive Testing**
   - Unit tests for API client components
   - Mock-based testing for network interactions
   - Integration tests for end-to-end workflows

### Phase 3: Long-term Consideration (❓ Evaluate)
1. **Plugin Architecture**
   - Modular transit provider support (currently DB-specific)
   - Extensible profile system for different APIs
   - Complex middleware patterns

2. **Advanced Data Processing**
   - Journey enrichment and manipulation
   - Complex fare calculation engines
   - Multi-modal transport integration

### Intentionally Skipped (❌ Skip)
1. **Multi-Provider Support**
   - Reason: Better-Bahn is specifically focused on Deutsche Bahn
   - Trade-off: Simpler architecture vs. broader compatibility

2. **Complex Promise/Async Patterns**
   - Reason: Python's async patterns differ significantly from JavaScript
   - Trade-off: Direct request handling vs. complex async orchestration

3. **Browser/Client-side Compatibility**
   - Reason: Better-Bahn targets CLI and mobile apps, not browsers
   - Trade-off: Simpler deployment vs. web compatibility

**Consequences**:

**Positive**:
- Improved reliability through structured error handling
- Better developer experience with clear error messages
- Maintainable architecture following proven patterns
- Gradual migration path without breaking existing functionality

**Negative**:
- Additional complexity in initial implementation
- Need for comprehensive testing of new error handling paths
- Migration effort required for existing error handling code

**Risk Mitigation**:
- Implement changes incrementally with backward compatibility
- Maintain existing CLI interface while enhancing error reporting
- Add comprehensive testing for new error handling patterns

---

## ADR-002: Data Model Alignment with hafas-client

**Status**: Accepted  
**Date**: 2024-09-16  
**Context**:

The hafas-client defines standardized data structures for public transport entities (Journey, Stop, Leg, Line, Location, etc.). Better-Bahn currently uses ad-hoc data structures that could benefit from alignment with these established patterns.

**Decision**:

We will create a unified data model that aligns with hafas-client naming conventions where practical, while maintaining compatibility with Deutsche Bahn's specific API responses.

### Core Entity Alignment

| hafas-client | Better-Bahn Current | Better-Bahn Proposed | Decision |
|--------------|--------------------|--------------------|-----------|
| `Journey` | `verbindung` (dict) | `Connection` | ✅ Align with semantic clarity |
| `Leg` | `teilstrecke` (dict) | `ConnectionSegment` | ✅ Align with hafas-client |
| `Stop`/`Station` | `bahnhof` (dict) | `Station` | ✅ Align with hafas-client |
| `Line` | `linie` (dict) | `TransportLine` | ✅ Align with hafas-client |
| `Location` | Mixed handling | `Location` | ✅ Align with hafas-client |

### Naming Convention Strategy

1. **External API Compatibility**: Maintain compatibility with DB API field names in raw responses
2. **Internal Consistency**: Use English, hafas-client-aligned names for internal data structures  
3. **Clear Mapping**: Provide explicit mapping between DB API responses and internal models
4. **German Documentation**: Keep German names in user-facing documentation and CLI output

### Implementation Approach

```python
# Proposed unified data model (inspired by hafas-client)
@dataclass
class Location:
    """Geographic location (station, point of interest, address)"""
    id: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: str = "station"  # station, poi, address
    
@dataclass 
class Stop:
    """A stop/station with platform and timing information"""
    location: Location
    departure: Optional[datetime] = None
    arrival: Optional[datetime] = None
    platform: Optional[str] = None
    delay: Optional[int] = None  # seconds
    cancelled: bool = False

@dataclass
class Leg:
    """A single transport leg within a journey"""
    origin: Stop
    destination: Stop  
    line: Optional['TransportLine'] = None
    duration: Optional[int] = None  # seconds
    distance: Optional[int] = None  # meters
    mode: str = "train"  # train, bus, walk, etc.

@dataclass
class Journey:
    """Complete journey with multiple legs"""
    legs: List[Leg]
    price: Optional[float] = None
    currency: str = "EUR"
    departure: Optional[datetime] = None
    arrival: Optional[datetime] = None
    duration: Optional[int] = None  # seconds
    transfers: int = 0
```

**Consequences**:

**Positive**:
- Improved consistency with established public transport data standards
- Better interoperability potential with other transit tools
- Clearer data structure documentation and examples
- Enhanced type safety and validation

**Negative**:  
- Migration effort for existing code using current data structures
- Additional abstraction layer between API responses and internal models
- Potential confusion during transition period

**Mitigation**:
- Implement gradual migration with adapter patterns
- Maintain backward compatibility during transition
- Create comprehensive mapping documentation
- Add validation for data model consistency

---

## ADR-003: Rate Limiting and API Client Architecture

**Status**: Accepted  
**Date**: 2024-09-16  
**Context**:

Current Better-Bahn implementation uses simple `time.sleep(0.5)` for rate limiting. hafas-client demonstrates more sophisticated throttling, retry logic, and configurable rate limiting that could improve reliability and prevent API abuse.

**Decision**: 

Implement a configurable API client architecture inspired by hafas-client's approach:

### Rate Limiting Strategy
- **Default**: 500ms delay between requests (current behavior)
- **Configurable**: Allow environment variable override
- **Adaptive**: Exponential backoff for rate limit responses (429)
- **Respectful**: Increase delays for server errors (5xx)

### Client Architecture
```python
class DBAPIClient:
    def __init__(self, config: DBAPIConfig):
        self.config = config
        self.session = requests.Session()
        self._last_request_time = 0
        
    def _throttle(self):
        # Implement configurable throttling
        
    def _retry_request(self, request_func, max_retries=3):
        # Implement exponential backoff retry logic
```

### Configuration Options
- Rate limit delay (default: 0.5s)
- Maximum retries (default: 3)
- Timeout settings (default: 30s)
- User agent customization
- Product filtering (ICE, IC, Regional, etc.)

**Consequences**:

**Positive**:
- More reliable API interactions with proper retry logic
- Configurable behavior for different deployment scenarios  
- Better adherence to API rate limiting requirements
- Improved error recovery and resilience

**Negative**:
- Increased complexity in request handling
- Additional configuration management required
- Potential performance impact from retry logic

**Implementation Priority**: Phase 1 (immediate adoption)

---

## ADR-004: Documentation Structure Enhancement

**Status**: Accepted  
**Date**: 2024-09-16  
**Context**: 

hafas-client demonstrates excellent documentation organization with method-specific files, comprehensive examples, and clear separation between API reference and usage guides. Better-Bahn currently has consolidated documentation that could benefit from this structure.

**Decision**:

Reorganize documentation following hafas-client patterns while maintaining existing German documentation:

### Proposed Structure
```
docs/
├── api/                    # API-specific documentation  
│   ├── README.md          # API overview
│   ├── vbid-resolution.md # Endpoint-specific docs
│   ├── connection-search.md
│   └── error-handling.md  # Comprehensive error guide
├── guides/                # Usage and integration guides
│   ├── getting-started.md
│   ├── split-ticket-analysis.md 
│   └── troubleshooting.md
├── examples/              # Code examples
│   ├── basic-usage.py
│   └── advanced-patterns.py
└── reference/             # Reference documentation
    ├── DECISIONS.md       # This file
    ├── hafas-client-comparison.md
    └── data-models.md
```

### Content Strategy
- **German primary**: Keep German as primary language for user documentation
- **English technical**: Use English for technical API and architecture documentation  
- **Bilingual examples**: Provide code examples with German comments
- **Cross-references**: Link between German and English documentation

**Consequences**:

**Positive**:
- Improved findability of specific information
- Better separation of concerns in documentation
- Enhanced developer experience with targeted guides
- Easier maintenance and updates

**Negative**:
- Documentation reorganization effort required
- Potential confusion during transition
- Need to maintain consistency across multiple files

**Implementation Priority**: Phase 2 (medium-term enhancement)

---

## ADR-005: Flutter Integration Patterns  

**Status**: Proposed  
**Date**: 2024-09-16  
**Context**:

Better-Bahn includes a Flutter mobile app that currently implements its own API client patterns. The hafas-client analysis suggests opportunities for consistency between Python CLI and Flutter implementations.

**Decision**: 

Create consistent patterns between Python and Dart implementations where practical:

### Shared Concepts
- **Error Handling**: Similar error type hierarchy in Dart
- **Configuration**: Consistent configuration patterns
- **Data Models**: Aligned data structure naming
- **Rate Limiting**: Similar throttling behavior

### Flutter-Specific Adaptations
```dart
// Dart adaptation of Python error handling
abstract class DBAPIException implements Exception {
  final String message;
  final String? code;
  final bool isServerError;
  
  const DBAPIException(this.message, {this.code, this.isServerError = false});
}

class DBNetworkException extends DBAPIException {
  const DBNetworkException(String message) : super(message, code: 'NETWORK_ERROR');
}
```

### Implementation Strategy
- Maintain platform-specific optimizations
- Share configuration and error handling patterns  
- Align data model naming conventions
- Create consistent developer experience

**Consequences**:

**Positive**:
- Consistent developer experience across platforms
- Shared mental models for error handling and configuration
- Easier maintenance with aligned patterns

**Negative**:
- Additional coordination required between Python and Dart code
- Platform-specific optimizations might be constrained
- Migration effort for existing Flutter code

**Implementation Priority**: Phase 3 (long-term consideration)

---

## Decision Impact Summary

### Immediate Implementation (Phase 1)
- [x] **Error Handling**: Structured error hierarchy
- [x] **CLI Enhancement**: Better error messages and guidance  
- [x] **Basic Configuration**: Environment variable support

### Medium-term Enhancement (Phase 2)  
- [ ] **Caching**: Response caching with TTL
- [ ] **Documentation**: Reorganized structure following hafas-client
- [ ] **Testing**: Comprehensive test suite

### Long-term Consideration (Phase 3)
- [ ] **Flutter Alignment**: Consistent patterns across platforms
- [ ] **Advanced Features**: Complex rate limiting, monitoring
- [ ] **Extensibility**: Plugin architecture evaluation

### Explicitly Rejected
- ❌ **Multi-provider Support**: Focus remains on Deutsche Bahn
- ❌ **Browser Compatibility**: CLI and mobile focus maintained
- ❌ **Complex Async Patterns**: Keep Python patterns simple and direct

This ADL ensures that Better-Bahn adopts proven patterns from hafas-client while maintaining its focused scope and existing strengths.