"""
Masterdata loader for Deutsche Bahn Timetables API.

This module provides functionality to load, validate, and provide strongly typed
masterdata objects with proper error handling and schema validation.
"""

import json
import yaml
from typing import Optional, Dict, Any
from pathlib import Path
import jsonschema
from masterdata_models import TimetableMasterdata


class MasterdataValidationError(Exception):
    """Raised when masterdata validation fails."""
    pass


class MasterdataLoader:
    """Loader for timetable masterdata with validation and caching."""
    
    def __init__(self, data_dir: Optional[str] = None, schema_dir: Optional[str] = None):
        """
        Initialize the masterdata loader.
        
        Args:
            data_dir: Directory containing YAML masterdata files
            schema_dir: Directory containing JSON schema files
        """
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
        self.schema_dir = Path(schema_dir) if schema_dir else Path(__file__).parent / "schemas"
        self._cached_masterdata: Optional[TimetableMasterdata] = None
        self._cached_schema: Optional[Dict[str, Any]] = None
    
    def load_schema(self) -> Dict[str, Any]:
        """Load and cache the JSON schema for validation."""
        if self._cached_schema is not None:
            return self._cached_schema
        
        schema_path = self.schema_dir / "timetables.schema.json"
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                self._cached_schema = schema
                return schema
        except FileNotFoundError:
            raise MasterdataValidationError(
                f"Schema file not found: {schema_path}. "
                "Please ensure schemas/timetables.schema.json exists."
            )
        except json.JSONDecodeError as e:
            raise MasterdataValidationError(
                f"Invalid JSON in schema file {schema_path}: {e}"
            )
        except Exception as e:
            raise MasterdataValidationError(
                f"Unexpected error loading schema from {schema_path}: {e}"
            )
    
    def validate_yaml_against_schema(self, data: Dict[str, Any]) -> None:
        """
        Validate YAML data against JSON schema.
        
        Args:
            data: Parsed YAML data to validate
            
        Raises:
            MasterdataValidationError: If validation fails
        """
        try:
            schema = self.load_schema()
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            # Provide more user-friendly error messages
            error_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            raise MasterdataValidationError(
                f"Schema validation failed at {error_path}: {e.message}\n"
                f"Invalid value: {e.instance}"
            )
        except jsonschema.SchemaError as e:
            raise MasterdataValidationError(
                f"Invalid schema definition: {e.message}"
            )
    
    def load_timetable_masterdata(self, filename: str = "Timetables-1.0.213.yaml") -> TimetableMasterdata:
        """
        Load timetable masterdata from YAML file with validation.
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            TimetableMasterdata: Strongly typed masterdata object
            
        Raises:
            MasterdataValidationError: If file is missing, malformed, or validation fails
        """
        yaml_path = self.data_dir / filename
        
        # Check if file exists
        if not yaml_path.exists():
            raise MasterdataValidationError(
                f"Masterdata file not found: {yaml_path}. "
                f"Please ensure the file exists in the data directory."
            )
        
        try:
            # Load YAML file
            with open(yaml_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            if raw_data is None:
                raise MasterdataValidationError(
                    f"YAML file {yaml_path} is empty or contains only null values."
                )
            
            if not isinstance(raw_data, dict):
                raise MasterdataValidationError(
                    f"YAML file {yaml_path} does not contain a valid object structure. "
                    f"Expected object, got {type(raw_data).__name__}."
                )
            
            # Validate against schema
            self.validate_yaml_against_schema(raw_data)
            
            # Create strongly typed masterdata object
            masterdata = TimetableMasterdata.from_dict(raw_data)
            
            # Additional validation
            self._validate_masterdata_completeness(masterdata)
            
            # Cache the result
            self._cached_masterdata = masterdata
            
            # Print hash for traceability
            print("✓ Timetable masterdata loaded successfully")
            print(f"  Version: {masterdata.info.version}")
            print(f"  Title: {masterdata.info.title}")
            print(f"  SHA256: {masterdata.data_hash}")
            print(f"  Schemas available: {sum(1 for v in masterdata.get_schema_summary()['available_schemas'].values() if v)}/6")
            
            return masterdata
            
        except yaml.YAMLError as e:
            raise MasterdataValidationError(
                f"Invalid YAML syntax in {yaml_path}: {e}. "
                "Please check the file format and structure."
            )
        except KeyError as e:
            raise MasterdataValidationError(
                f"Missing required field in masterdata: {e}. "
                "The YAML file structure is incomplete."
            )
        except ValueError as e:
            raise MasterdataValidationError(
                f"Invalid data in masterdata: {e}"
            )
        except Exception as e:
            raise MasterdataValidationError(
                f"Unexpected error loading masterdata from {yaml_path}: {e}"
            )
    
    def _validate_masterdata_completeness(self, masterdata: TimetableMasterdata) -> None:
        """
        Validate that masterdata contains expected components.
        
        Args:
            masterdata: Loaded masterdata to validate
            
        Raises:
            MasterdataValidationError: If critical components are missing
        """
        # Check required info fields
        if not masterdata.info.title:
            raise MasterdataValidationError("API title is missing or empty")
        
        if not masterdata.info.version:
            raise MasterdataValidationError("API version is missing or empty")
        
        # Check OpenAPI version
        if not masterdata.openapi_version:
            raise MasterdataValidationError("OpenAPI version is missing")
        
        # Validate enum schemas contain expected values
        if masterdata.connection_status_schema:
            expected_statuses = {"w", "n", "a"}
            actual_statuses = set(masterdata.connection_status_schema.enum_values)
            if not expected_statuses.issubset(actual_statuses):
                missing = expected_statuses - actual_statuses
                raise MasterdataValidationError(
                    f"Connection status schema is missing expected values: {missing}"
                )
        
        if masterdata.delay_source_schema:
            expected_sources = {"L", "NA", "NM", "V", "IA", "IM", "A"}
            actual_sources = set(masterdata.delay_source_schema.enum_values)
            if not expected_sources.issubset(actual_sources):
                missing = expected_sources - actual_sources
                raise MasterdataValidationError(
                    f"Delay source schema is missing expected values: {missing}"
                )
    
    def get_cached_masterdata(self) -> Optional[TimetableMasterdata]:
        """
        Get cached masterdata if available.
        
        Returns:
            Cached masterdata or None if not loaded yet
        """
        return self._cached_masterdata
    
    def reload_masterdata(self, filename: str = "Timetables-1.0.213.yaml") -> TimetableMasterdata:
        """
        Force reload masterdata from file, bypassing cache.
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            TimetableMasterdata: Freshly loaded masterdata object
        """
        self._cached_masterdata = None
        self._cached_schema = None
        return self.load_timetable_masterdata(filename)
    
    def validate_connection_data(self, connection_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate connection data against loaded schemas.
        
        Args:
            connection_data: Connection data to validate
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        if not self._cached_masterdata:
            errors['loader'] = "No masterdata loaded. Call load_timetable_masterdata() first."
            return errors
        
        masterdata = self._cached_masterdata
        
        # Validate connection status
        if 'cs' in connection_data:
            if not masterdata.validate_connection_status(connection_data['cs']):
                valid_values = masterdata.connection_status_schema.enum_values if masterdata.connection_status_schema else []
                errors['cs'] = f"Invalid connection status '{connection_data['cs']}'. Valid values: {valid_values}"
        
        # Validate EVA number
        if 'eva' in connection_data:
            if not masterdata.validate_eva_number(connection_data['eva']):
                errors['eva'] = f"Invalid EVA number '{connection_data['eva']}'. Must be a 6-8 digit integer."
        
        # Validate timestamp format
        if 'ts' in connection_data:
            ts = connection_data['ts']
            if not isinstance(ts, str) or len(ts) != 10 or not ts.isdigit():
                errors['ts'] = f"Invalid timestamp format '{ts}'. Expected 10-digit string in YYMMddHHmm format."
        
        return errors


# Global loader instance for easy access
_global_loader = MasterdataLoader()


def get_masterdata_loader() -> MasterdataLoader:
    """Get the global masterdata loader instance."""
    return _global_loader


def load_timetable_masterdata(filename: str = "Timetables-1.0.213.yaml") -> TimetableMasterdata:
    """
    Convenience function to load masterdata using the global loader.
    
    Args:
        filename: Name of the YAML file to load
        
    Returns:
        TimetableMasterdata: Loaded masterdata object
    """
    return _global_loader.load_timetable_masterdata(filename)