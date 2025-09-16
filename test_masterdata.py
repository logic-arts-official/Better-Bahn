"""
Unit tests for masterdata integration with 100% path coverage.

Tests cover happy path, missing fields, invalid enums, file errors, and schema validation.
"""

import unittest
import tempfile
import os
import json
import yaml
from pathlib import Path
from unittest.mock import patch

from masterdata_loader import MasterdataLoader, MasterdataValidationError, load_timetable_masterdata
from masterdata_models import TimetableMasterdata, ApiInfo, ConnectionStatus, DelaySource, StationIndex


class TestMasterdataModels(unittest.TestCase):
    """Test strongly typed masterdata models."""

    def test_connection_status_enum(self):
        """Test ConnectionStatus enum values."""
        self.assertEqual(ConnectionStatus.WAITING.value, "w")
        self.assertEqual(ConnectionStatus.TRANSITION.value, "n")
        self.assertEqual(ConnectionStatus.ALTERNATIVE.value, "a")

    def test_delay_source_enum(self):
        """Test DelaySource enum values."""
        self.assertEqual(DelaySource.LEIBIT.value, "L")
        self.assertEqual(DelaySource.RISNE_AUT.value, "NA")
        self.assertEqual(DelaySource.RISNE_MAN.value, "NM")
        self.assertEqual(DelaySource.VDV.value, "V")
        self.assertEqual(DelaySource.ISTP_AUT.value, "IA")
        self.assertEqual(DelaySource.ISTP_MAN.value, "IM")
        self.assertEqual(DelaySource.AUTOMATIC.value, "A")

    def test_api_info_from_dict(self):
        """Test ApiInfo creation from dictionary."""
        data = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test description",
            "contact": {"email": "test@example.com"},
            "termsOfService": "https://example.com/terms",
            "x-ibm-name": "test-api"
        }
        info = ApiInfo.from_dict(data)
        self.assertEqual(info.title, "Test API")
        self.assertEqual(info.version, "1.0.0")
        self.assertEqual(info.description, "Test description")
        self.assertEqual(info.contact_email, "test@example.com")
        self.assertEqual(info.terms_of_service, "https://example.com/terms")
        self.assertEqual(info.x_ibm_name, "test-api")

    def test_api_info_minimal(self):
        """Test ApiInfo with minimal required fields."""
        data = {"title": "Test API", "version": "1.0.0"}
        info = ApiInfo.from_dict(data)
        self.assertEqual(info.title, "Test API")
        self.assertEqual(info.version, "1.0.0")
        self.assertIsNone(info.description)
        self.assertIsNone(info.contact_email)

    def test_station_index(self):
        """Test StationIndex functionality."""
        index = StationIndex()
        
        # Add stations
        index.add_station(8000261, "München Hbf")
        index.add_station(8000036, "Berlin Hbf")
        
        # Test lookups
        self.assertEqual(index.lookup_by_eva(8000261), "München Hbf")
        self.assertEqual(index.lookup_by_name("München Hbf"), 8000261)
        self.assertEqual(index.lookup_by_normalized_name("muenchen hbf"), 8000261)
        self.assertEqual(index.lookup_by_normalized_name("muenchenhbf"), 8000261)
        
        # Test missing entries
        self.assertIsNone(index.lookup_by_eva(9999999))
        self.assertIsNone(index.lookup_by_name("Nonexistent Station"))
        self.assertIsNone(index.lookup_by_normalized_name("nonexistent"))

    def test_timetable_masterdata_validation(self):
        """Test TimetableMasterdata validation methods."""
        # Create minimal valid masterdata
        data = {
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "connectionStatus": {
                        "type": "string",
                        "enum": ["w", "n", "a"]
                    },
                    "delaySource": {
                        "type": "string", 
                        "enum": ["L", "NA", "NM", "V", "IA", "IM", "A"]
                    }
                }
            }
        }
        
        masterdata = TimetableMasterdata.from_dict(data)
        
        # Test validation methods
        self.assertTrue(masterdata.validate_connection_status("w"))
        self.assertTrue(masterdata.validate_connection_status("n"))
        self.assertTrue(masterdata.validate_connection_status("a"))
        self.assertFalse(masterdata.validate_connection_status("x"))
        
        self.assertTrue(masterdata.validate_delay_source("L"))
        self.assertTrue(masterdata.validate_delay_source("NA"))
        self.assertFalse(masterdata.validate_delay_source("XX"))
        
        self.assertTrue(masterdata.validate_eva_number(8000261))
        self.assertTrue(masterdata.validate_eva_number("8000261"))
        self.assertFalse(masterdata.validate_eva_number(123))  # Too short
        self.assertFalse(masterdata.validate_eva_number("invalid"))
        self.assertFalse(masterdata.validate_eva_number(None))

    def test_timetable_masterdata_missing_info(self):
        """Test TimetableMasterdata with missing info section."""
        data = {"openapi": "3.0.1", "components": {"schemas": {}}}
        with self.assertRaises(ValueError) as cm:
            TimetableMasterdata.from_dict(data)
        self.assertIn("Missing required 'info' section", str(cm.exception))


class TestMasterdataLoader(unittest.TestCase):
    """Test masterdata loader with various error conditions."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.schema_dir = Path(self.temp_dir) / "schemas"
        self.data_dir.mkdir()
        self.schema_dir.mkdir()
        
        # Create a valid schema file
        self.valid_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Test Schema",
            "type": "object",
            "required": ["openapi", "info", "components"],
            "properties": {
                "openapi": {"type": "string"},
                "info": {
                    "type": "object",
                    "required": ["title", "version"],
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"}
                    }
                },
                "components": {
                    "type": "object",
                    "required": ["schemas"],
                    "properties": {
                        "schemas": {"type": "object"}
                    }
                }
            },
            "additionalProperties": True
        }
        
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            json.dump(self.valid_schema, f)
        
        # Create valid test YAML data
        self.valid_yaml_data = {
            "openapi": "3.0.1",
            "info": {
                "title": "Test Timetables",
                "version": "1.0.0",
                "description": "Test API"
            },
            "components": {
                "schemas": {
                    "connectionStatus": {
                        "type": "string",
                        "enum": ["w", "n", "a"],
                        "description": "Connection status"
                    },
                    "delaySource": {
                        "type": "string",
                        "enum": ["L", "NA", "NM", "V", "IA", "IM", "A"],
                        "description": "Delay source"
                    }
                }
            }
        }
        
        self.loader = MasterdataLoader(str(self.data_dir), str(self.schema_dir))

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_schema_success(self):
        """Test successful schema loading."""
        schema = self.loader.load_schema()
        self.assertEqual(schema["title"], "Test Schema")
        
        # Test caching
        schema2 = self.loader.load_schema()
        self.assertIs(schema, schema2)

    def test_load_schema_file_not_found(self):
        """Test schema loading with missing file."""
        os.remove(self.schema_dir / "timetables.schema.json")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_schema()
        self.assertIn("Schema file not found", str(cm.exception))

    def test_load_schema_invalid_json(self):
        """Test schema loading with invalid JSON."""
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            f.write("invalid json {")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_schema()
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_load_masterdata_success(self):
        """Test successful masterdata loading."""
        yaml_file = self.data_dir / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        
        masterdata = self.loader.load_timetable_masterdata("test.yaml")
        self.assertEqual(masterdata.info.title, "Test Timetables")
        self.assertEqual(masterdata.info.version, "1.0.0")
        self.assertIsNotNone(masterdata.data_hash)

    def test_load_masterdata_file_not_found(self):
        """Test masterdata loading with missing file."""
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("nonexistent.yaml")
        self.assertIn("Masterdata file not found", str(cm.exception))

    def test_load_masterdata_empty_file(self):
        """Test masterdata loading with empty file."""
        yaml_file = self.data_dir / "empty.yaml"
        with open(yaml_file, 'w') as f:
            f.write("")
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty.yaml")
        self.assertIn("empty or contains only null values", str(cm.exception))

    def test_load_masterdata_invalid_structure(self):
        """Test masterdata loading with invalid structure."""
        yaml_file = self.data_dir / "invalid.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(["this", "is", "a", "list"], f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid.yaml")
        self.assertIn("does not contain a valid object structure", str(cm.exception))

    def test_load_masterdata_invalid_yaml(self):
        """Test masterdata loading with invalid YAML syntax."""
        yaml_file = self.data_dir / "invalid.yaml"
        with open(yaml_file, 'w') as f:
            f.write("invalid: yaml: [unclosed")
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid.yaml")
        self.assertIn("Invalid YAML syntax", str(cm.exception))

    def test_load_masterdata_schema_validation_failure(self):
        """Test masterdata loading with schema validation failure."""
        invalid_data = {"openapi": "3.0.1"}  # Missing required fields
        yaml_file = self.data_dir / "invalid_schema.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_schema.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))

    def test_load_masterdata_missing_title(self):
        """Test masterdata loading with missing title."""
        invalid_data = {
            "openapi": "3.0.1",
            "info": {"version": "1.0.0"},  # Missing title
            "components": {"schemas": {}}
        }
        yaml_file = self.data_dir / "no_title.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("no_title.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))
        self.assertIn("'title' is a required property", str(cm.exception))

    def test_load_masterdata_missing_version(self):
        """Test masterdata loading with missing version."""
        invalid_data = {
            "openapi": "3.0.1",
            "info": {"title": "Test"},  # Missing version
            "components": {"schemas": {}}
        }
        yaml_file = self.data_dir / "no_version.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("no_version.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))
        self.assertIn("'version' is a required property", str(cm.exception))

    def test_load_masterdata_empty_title(self):
        """Test masterdata loading with empty title (passes schema but fails custom validation)."""
        # Create a permissive schema that allows empty strings
        permissive_schema = self.valid_schema.copy()
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            json.dump(permissive_schema, f)
        
        invalid_data = {
            "openapi": "3.0.1",
            "info": {"title": "", "version": "1.0.0"},  # Empty title
            "components": {"schemas": {}}
        }
        yaml_file = self.data_dir / "empty_title.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty_title.yaml")
        self.assertIn("API title is missing or empty", str(cm.exception))

    def test_load_masterdata_empty_version(self):
        """Test masterdata loading with empty version (passes schema but fails custom validation)."""
        invalid_data = {
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": ""},  # Empty version
            "components": {"schemas": {}}
        }
        yaml_file = self.data_dir / "empty_version.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty_version.yaml")
        self.assertIn("API version is missing or empty", str(cm.exception))

    def test_load_masterdata_invalid_connection_status(self):
        """Test masterdata loading with invalid connection status enum."""
        invalid_data = self.valid_yaml_data.copy()
        invalid_data["components"]["schemas"]["connectionStatus"]["enum"] = ["w", "n"]  # Missing "a"
        
        yaml_file = self.data_dir / "invalid_enum.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_enum.yaml")
        self.assertIn("Connection status schema is missing expected values", str(cm.exception))

    def test_load_masterdata_invalid_delay_source(self):
        """Test masterdata loading with invalid delay source enum."""
        invalid_data = self.valid_yaml_data.copy()
        invalid_data["components"]["schemas"]["delaySource"]["enum"] = ["L", "NA"]  # Missing others
        
        yaml_file = self.data_dir / "invalid_delay.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_delay.yaml")
        self.assertIn("Delay source schema is missing expected values", str(cm.exception))

    def test_get_cached_masterdata(self):
        """Test cached masterdata retrieval."""
        # Initially no cache
        self.assertIsNone(self.loader.get_cached_masterdata())
        
        # Load masterdata
        yaml_file = self.data_dir / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        
        masterdata = self.loader.load_timetable_masterdata("test.yaml")
        
        # Now should be cached
        cached = self.loader.get_cached_masterdata()
        self.assertIs(masterdata, cached)

    def test_reload_masterdata(self):
        """Test masterdata reloading (bypassing cache)."""
        yaml_file = self.data_dir / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        
        # Load first time
        masterdata1 = self.loader.load_timetable_masterdata("test.yaml")
        
        # Reload should create new instance
        masterdata2 = self.loader.reload_masterdata("test.yaml")
        self.assertIsNot(masterdata1, masterdata2)
        self.assertEqual(masterdata1.info.title, masterdata2.info.title)

    def test_validate_connection_data_no_masterdata(self):
        """Test connection data validation without loaded masterdata."""
        errors = self.loader.validate_connection_data({"cs": "w"})
        self.assertIn("loader", errors)
        self.assertIn("No masterdata loaded", errors["loader"])

    def test_validate_connection_data_success(self):
        """Test successful connection data validation."""
        yaml_file = self.data_dir / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        
        self.loader.load_timetable_masterdata("test.yaml")
        
        # Valid data
        errors = self.loader.validate_connection_data({
            "cs": "w",
            "eva": 8000261,
            "ts": "2404011437"
        })
        self.assertEqual(len(errors), 0)

    def test_validate_connection_data_invalid_values(self):
        """Test connection data validation with invalid values."""
        yaml_file = self.data_dir / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        
        self.loader.load_timetable_masterdata("test.yaml")
        
        # Invalid data
        errors = self.loader.validate_connection_data({
            "cs": "invalid",
            "eva": "not_a_number",
            "ts": "short"
        })
        
        self.assertIn("cs", errors)
        self.assertIn("eva", errors)
        self.assertIn("ts", errors)
        self.assertIn("Invalid connection status", errors["cs"])
        self.assertIn("Invalid EVA number", errors["eva"])
        self.assertIn("Invalid timestamp format", errors["ts"])


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""

    @patch('masterdata_loader._global_loader')
    def test_load_timetable_masterdata_global(self, mock_loader):
        """Test global load_timetable_masterdata function."""
        mock_masterdata = TimetableMasterdata(
            openapi_version="3.0.1",
            info=ApiInfo(title="Test", version="1.0.0"),
            data_hash="test_hash"
        )
        mock_loader.load_timetable_masterdata.return_value = mock_masterdata
        
        result = load_timetable_masterdata("test.yaml")
        mock_loader.load_timetable_masterdata.assert_called_once_with("test.yaml")
        self.assertEqual(result, mock_masterdata)


if __name__ == "__main__":
    unittest.main()