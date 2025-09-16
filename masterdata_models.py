"""
Masterdata models for Deutsche Bahn Timetables API.

This module provides strongly typed dataclasses for parsing and validating
timetable masterdata from YAML files, with proper null-safety and validation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union
from enum import Enum
import hashlib
import json


class ConnectionStatus(Enum):
    """Connection status enumeration."""
    WAITING = "w"          # This connection is waiting
    TRANSITION = "n"       # This connection CANNOT wait  
    ALTERNATIVE = "a"      # Alternative connection


class DelaySource(Enum):
    """Delay source enumeration."""
    LEIBIT = "L"          # LeiBit/LeiDis
    RISNE_AUT = "NA"      # IRIS-NE (automatisch)
    RISNE_MAN = "NM"      # IRIS-NE (manuell)
    VDV = "V"             # Prognosen durch dritte EVU über VDVin
    ISTP_AUT = "IA"       # ISTP automatisch
    ISTP_MAN = "IM"       # ISTP manuell
    AUTOMATIC = "A"       # Automatische Prognose


class DistributorType(Enum):
    """Distributor type enumeration."""
    # Values will be populated from actual YAML data
    pass


@dataclass
class ApiInfo:
    """API information from the info section."""
    title: str
    version: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    terms_of_service: Optional[str] = None
    x_ibm_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiInfo':
        """Create ApiInfo from dictionary."""
        contact = data.get('contact', {})
        return cls(
            title=data['title'],
            version=data['version'],
            description=data.get('description'),
            contact_email=contact.get('email') if contact else None,
            terms_of_service=data.get('termsOfService'),
            x_ibm_name=data.get('x-ibm-name')
        )


@dataclass
class ConnectionProperty:
    """Property definition for connection schema."""
    ref: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    format: Optional[str] = None
    xml_attribute: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionProperty':
        """Create ConnectionProperty from dictionary."""
        xml_config = data.get('xml', {})
        return cls(
            ref=data.get('$ref'),
            description=data.get('description'),
            type=data.get('type'),
            format=data.get('format'),
            xml_attribute=xml_config.get('attribute', False)
        )


@dataclass
class ConnectionSchema:
    """Schema definition for connection objects."""
    description: str
    type: str
    required: List[str]
    properties: Dict[str, ConnectionProperty]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionSchema':
        """Create ConnectionSchema from dictionary."""
        properties = {}
        for prop_name, prop_data in data.get('properties', {}).items():
            properties[prop_name] = ConnectionProperty.from_dict(prop_data)
        
        return cls(
            description=data.get('description', ''),
            type=data.get('type', 'object'),
            required=data.get('required', []),
            properties=properties
        )


@dataclass
class EnumSchema:
    """Schema definition for enumeration types."""
    description: str
    type: str
    enum_values: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnumSchema':
        """Create EnumSchema from dictionary."""
        return cls(
            description=data.get('description', ''),
            type=data.get('type', 'string'),
            enum_values=data.get('enum', [])
        )


@dataclass
class StationIndex:
    """Index for fast station lookup."""
    eva_to_name: Dict[int, str] = field(default_factory=dict)
    name_to_eva: Dict[str, int] = field(default_factory=dict)
    normalized_name_to_eva: Dict[str, int] = field(default_factory=dict)

    def add_station(self, eva: int, name: str) -> None:
        """Add a station to the index."""
        self.eva_to_name[eva] = name
        self.name_to_eva[name] = eva
        # Normalize: lowercase, remove spaces and special chars
        normalized = name.lower().replace(' ', '').replace('-', '').replace('ü', 'ue').replace('ö', 'oe').replace('ä', 'ae').replace('ß', 'ss')
        self.normalized_name_to_eva[normalized] = eva

    def lookup_by_name(self, name: str) -> Optional[int]:
        """Lookup EVA number by station name (exact match)."""
        return self.name_to_eva.get(name)

    def lookup_by_normalized_name(self, name: str) -> Optional[int]:
        """Lookup EVA number by normalized station name."""
        normalized = name.lower().replace(' ', '').replace('-', '').replace('ü', 'ue').replace('ö', 'oe').replace('ä', 'ae').replace('ß', 'ss')
        return self.normalized_name_to_eva.get(normalized)

    def lookup_by_eva(self, eva: int) -> Optional[str]:
        """Lookup station name by EVA number."""
        return self.eva_to_name.get(eva)

    def get_size(self) -> int:
        """Get the number of stations in the index."""
        return len(self.eva_to_name)


@dataclass
class TimetableMasterdata:
    """Complete timetable masterdata with strongly typed objects."""
    openapi_version: str
    info: ApiInfo
    connection_schema: Optional[ConnectionSchema] = None
    connection_status_schema: Optional[EnumSchema] = None
    delay_source_schema: Optional[EnumSchema] = None
    distributor_message_schema: Optional[Dict[str, Any]] = None
    distributor_type_schema: Optional[EnumSchema] = None
    timetable_stop_schema: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    data_hash: Optional[str] = None
    station_index: StationIndex = field(default_factory=StationIndex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimetableMasterdata':
        """Create TimetableMasterdata from dictionary with validation."""
        # Extract info
        info_data = data.get('info', {})
        if not info_data:
            raise ValueError("Missing required 'info' section in masterdata")
        
        info = ApiInfo.from_dict(info_data)
        
        # Extract schemas
        components = data.get('components', {})
        schemas = components.get('schemas', {})
        
        connection_schema = None
        connection_status_schema = None
        delay_source_schema = None
        distributor_type_schema = None
        
        if 'connection' in schemas:
            connection_schema = ConnectionSchema.from_dict(schemas['connection'])
        
        if 'connectionStatus' in schemas:
            connection_status_schema = EnumSchema.from_dict(schemas['connectionStatus'])
        
        if 'delaySource' in schemas:
            delay_source_schema = EnumSchema.from_dict(schemas['delaySource'])
            
        if 'distributorType' in schemas:
            distributor_type_schema = EnumSchema.from_dict(schemas['distributorType'])
        
        # Calculate data hash for traceability
        data_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        data_hash = hashlib.sha256(data_json.encode('utf-8')).hexdigest()
        
        # Create station index (would be populated from actual station data if available)
        station_index = StationIndex()
        
        return cls(
            openapi_version=data.get('openapi', ''),
            info=info,
            connection_schema=connection_schema,
            connection_status_schema=connection_status_schema,
            delay_source_schema=delay_source_schema,
            distributor_message_schema=schemas.get('distributorMessage'),
            distributor_type_schema=distributor_type_schema,
            timetable_stop_schema=schemas.get('timetableStop'),
            raw_data=data,
            data_hash=data_hash,
            station_index=station_index
        )

    def validate_connection_status(self, status: str) -> bool:
        """Validate a connection status value."""
        if not self.connection_status_schema:
            return False
        return status in self.connection_status_schema.enum_values

    def validate_delay_source(self, source: str) -> bool:
        """Validate a delay source value."""
        if not self.delay_source_schema:
            return False
        return source in self.delay_source_schema.enum_values

    def validate_eva_number(self, eva: Union[int, str]) -> bool:
        """Validate an EVA station number."""
        try:
            eva_int = int(eva)
            # EVA numbers are typically 6-8 digits
            return 100000 <= eva_int <= 99999999
        except (ValueError, TypeError):
            return False

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get a summary of available schemas."""
        return {
            'openapi_version': self.openapi_version,
            'api_title': self.info.title,
            'api_version': self.info.version,
            'data_hash': self.data_hash,
            'available_schemas': {
                'connection': self.connection_schema is not None,
                'connection_status': self.connection_status_schema is not None,
                'delay_source': self.delay_source_schema is not None,
                'distributor_message': self.distributor_message_schema is not None,
                'distributor_type': self.distributor_type_schema is not None,
                'timetable_stop': self.timetable_stop_schema is not None,
            },
            'connection_status_values': self.connection_status_schema.enum_values if self.connection_status_schema else [],
            'delay_source_values': self.delay_source_schema.enum_values if self.delay_source_schema else [],
            'station_index_size': len(self.station_index.eva_to_name)
        }