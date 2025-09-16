#!/usr/bin/env python3
"""
Better-Bahn Masterdata Test Suite (merged)

Enthält:
1) Pipeline-/Integrations-Tests gegen das Modul `main`
2) Streng typisierte Unittests gegen `masterdata_loader` und `masterdata_models`
"""

import sys
import os
import json
import unittest
import tempfile
from pathlib import Path
from datetime import datetime

# Optionales YAML für Loader-Tests
try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

# --- Pfadkonfiguration, damit `main` importierbar ist ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Module der Pipeline
import main  # noqa: E402

# Module der typisierten Masterdata-Schicht
from masterdata_loader import (  # noqa: E402
    MasterdataLoader,
    MasterdataValidationError,
    load_timetable_masterdata as load_timetable_masterdata_global,
)
from masterdata_models import (  # noqa: E402
    TimetableMasterdata,
    ApiInfo,
    ConnectionStatus,
    DelaySource,
    StationIndex,
)


# ========== 1) Pipeline-/Integrations-Tests gegen `main` ==========

class TestMasterdataProcessingPipeline(unittest.TestCase):
    """Tests für die komplette Masterdata-Processing-Pipeline in `main`."""

    def test_schema_loading(self):
        schema = main.load_masterdata_schema()
        self.assertIsNotNone(schema)
        self.assertEqual(schema.get('title'), 'Better-Bahn Masterdata Schema')

    def test_version_management(self):
        info = main.load_timetables_version()
        self.assertIsNotNone(info)
        self.assertIn('version', info)
        self.assertIn('file_sha256', info)

    def test_station_name_normalization(self):
        cases = [
            ("München Hauptbahnhof", "munchen hauptbahnhof"),
            ("Köln Hbf", "koln hbf"),
            ("Düsseldorf Flughafen", "dusseldorf flughafen"),
            ("Würzburg Hbf", "wurzburg hbf"),
            ("François Mitterrand", "francois mitterrand"),
            ("  Extra   Spaces  ", "extra spaces"),
        ]
        for original, expected in cases:
            self.assertEqual(main.normalize_station_name(original), expected)

    def test_eva_number_validation(self):
        valid = [8000261, 8011160, 1000000, 9999999]
        invalid = [123, 999999, 10000000, "invalid", None]
        for eva in valid:
            self.assertTrue(main.validate_eva_number(eva))
        for eva in invalid:
            self.assertFalse(main.validate_eva_number(eva))

    def test_station_data_validation(self):
        valid_station = {
            'id': 'TEST_STATION_001',
            'name': 'München Hauptbahnhof',
            'name_normalized': main.normalize_station_name('München Hauptbahnhof'),
            'eva': 8000261,
            'lat': 48.1400,
            'lon': 11.5583,
            'ds100': 'MH',
            'platforms': ['1', '2', '3', '4'],
            'external_ids': {'hafas': 'test_id'},
            'metadata': {'state': 'Bayern', 'category': '1'}
        }
        is_valid, errors = main.validate_station_data(valid_station)
        self.assertTrue(is_valid, msg=f"Unexpected errors: {errors}")

        invalid_station = {'id': '', 'name': '', 'eva': 123}
        is_valid, errors = main.validate_station_data(invalid_station)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_service_data_validation(self):
        valid_service = {
            'id': 'ICE_123_20240101',
            'product': 'ICE',
            'stops': [
                {'station_id': 'TEST_STATION_001', 'sequence': 0, 'departure_planned': '2024-01-01T08:00:00Z', 'platform': '1'},
                {'station_id': 'TEST_STATION_002', 'sequence': 1, 'arrival_planned': '2024-01-01T10:00:00Z', 'platform': '2'}
            ],
            'operating_days': {'monday': True, 'tuesday': True, 'wednesday': True, 'thursday': True, 'friday': True, 'saturday': False, 'sunday': False}
        }
        is_valid, errors = main.validate_service_data(valid_service)
        self.assertTrue(is_valid, msg=f"Unexpected errors: {errors}")

        invalid_service = {
            'id': 'ICE_INVALID',
            'product': 'ICE',
            'stops': [
                {'station_id': 'TEST_STATION_001', 'sequence': 0, 'departure_planned': '2024-01-01T10:00:00Z'},
                {'station_id': 'TEST_STATION_002', 'sequence': 2, 'arrival_planned': '2024-01-01T08:00:00Z'}
            ],
            'operating_days': {'monday': True, 'tuesday': True, 'wednesday': True, 'thursday': True, 'friday': True, 'saturday': False, 'sunday': False}
        }
        is_valid, errors = main.validate_service_data(invalid_service)
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(errors), 1)

    def test_adjacency_computation(self):
        stations = [
            {'id': 'STA', 'name': 'Station A'},
            {'id': 'STB', 'name': 'Station B'},
            {'id': 'STC', 'name': 'Station C'}
        ]
        services = [{
            'id': 'SERVICE_1',
            'product': 'ICE',
            'stops': [
                {'station_id': 'STA', 'sequence': 0, 'departure_planned': '08:00:00Z'},
                {'station_id': 'STB', 'sequence': 1, 'arrival_planned': '09:00:00Z', 'departure_planned': '09:05:00Z'},
                {'station_id': 'STC', 'sequence': 2, 'arrival_planned': '10:00:00Z'}
            ],
            'operating_days': {'monday': True, 'tuesday': True, 'wednesday': True, 'thursday': True, 'friday': True, 'saturday': False, 'sunday': False}
        }]
        routing = main.precompute_adjacency_data(stations, services)
        self.assertIn('adjacency', routing)
        self.assertIn('route_segments', routing)
        self.assertEqual(len(routing['route_segments']), 2)
        self.assertIn('STA', routing['adjacency'])
        self.assertIn('STB', routing['adjacency']['STA'])

    def test_version_update_with_statistics_and_hash(self):
        stats = {
            'total_stations': 3,
            'total_services': 1,
            'last_updated': datetime.utcnow().isoformat() + "Z"
        }
        self.assertTrue(main.update_timetables_version(stats))
        updated = main.load_timetables_version()
        self.assertEqual(updated['statistics']['total_stations'], 3)
        self.assertEqual(updated['statistics']['total_services'], 1)

        timetables_path = os.path.join(PROJECT_ROOT, "data", "Timetables-1.0.213.yaml")
        file_hash = main.compute_file_hash(timetables_path)
        self.assertIsNotNone(file_hash)
        self.assertEqual(len(file_hash), 64)
        self.assertEqual(updated['file_sha256'], file_hash)


# ========== 2) Streng typisierte Unittests (Loader/Models) ==========

class TestMasterdataModels(unittest.TestCase):
    """Tests für stark typisierte Masterdata-Modelle."""

    def test_connection_status_enum(self):
        self.assertEqual(ConnectionStatus.WAITING.value, "w")
        self.assertEqual(ConnectionStatus.TRANSITION.value, "n")
        self.assertEqual(ConnectionStatus.ALTERNATIVE.value, "a")

    def test_delay_source_enum(self):
        self.assertEqual(DelaySource.LEIBIT.value, "L")
        self.assertEqual(DelaySource.RISNE_AUT.value, "NA")
        self.assertEqual(DelaySource.RISNE_MAN.value, "NM")
        self.assertEqual(DelaySource.VDV.value, "V")
        self.assertEqual(DelaySource.ISTP_AUT.value, "IA")
        self.assertEqual(DelaySource.ISTP_MAN.value, "IM")
        self.assertEqual(DelaySource.AUTOMATIC.value, "A")

    def test_api_info_from_dict(self):
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
        data = {"title": "Test API", "version": "1.0.0"}
        info = ApiInfo.from_dict(data)
        self.assertEqual(info.title, "Test API")
        self.assertEqual(info.version, "1.0.0")
        self.assertIsNone(info.description)
        self.assertIsNone(info.contact_email)

    def test_station_index(self):
        index = StationIndex()
        index.add_station(8000261, "München Hbf")
        index.add_station(8000036, "Berlin Hbf")
        self.assertEqual(index.lookup_by_eva(8000261), "München Hbf")
        self.assertEqual(index.lookup_by_name("München Hbf"), 8000261)
        self.assertEqual(index.lookup_by_normalized_name("muenchen hbf"), 8000261)
        self.assertEqual(index.lookup_by_normalized_name("muenchenhbf"), 8000261)
        self.assertIsNone(index.lookup_by_eva(9999999))
        self.assertIsNone(index.lookup_by_name("Nonexistent Station"))
        self.assertIsNone(index.lookup_by_normalized_name("nonexistent"))

    def test_timetable_masterdata_validation(self):
        data = {
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "connectionStatus": {"type": "string", "enum": ["w", "n", "a"]},
                    "delaySource": {"type": "string", "enum": ["L", "NA", "NM", "V", "IA", "IM", "A"]}
                }
            }
        }
        md = TimetableMasterdata.from_dict(data)
        self.assertTrue(md.validate_connection_status("w"))
        self.assertTrue(md.validate_connection_status("n"))
        self.assertTrue(md.validate_connection_status("a"))
        self.assertFalse(md.validate_connection_status("x"))
        self.assertTrue(md.validate_delay_source("L"))
        self.assertTrue(md.validate_delay_source("NA"))
        self.assertFalse(md.validate_delay_source("XX"))
        self.assertTrue(md.validate_eva_number(8000261))
        self.assertTrue(md.validate_eva_number("8000261"))
        self.assertFalse(md.validate_eva_number(123))
        self.assertFalse(md.validate_eva_number("invalid"))
        self.assertFalse(md.validate_eva_number(None))

    def test_timetable_masterdata_missing_info(self):
        data = {"openapi": "3.0.1", "components": {"schemas": {}}}
        with self.assertRaises(ValueError) as cm:
            TimetableMasterdata.from_dict(data)
        self.assertIn("Missing required 'info' section", str(cm.exception))


class TestMasterdataLoader(unittest.TestCase):
    """Tests für den Loader inkl. Fehlerpfade."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.schema_dir = Path(self.temp_dir) / "schemas"
        self.data_dir.mkdir()
        self.schema_dir.mkdir()

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
                    "properties": {"title": {"type": "string"}, "version": {"type": "string"}}
                },
                "components": {
                    "type": "object",
                    "required": ["schemas"],
                    "properties": {"schemas": {"type": "object"}}
                }
            },
            "additionalProperties": True
        }
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            json.dump(self.valid_schema, f)

        self.valid_yaml_data = {
            "openapi": "3.0.1",
            "info": {"title": "Test Timetables", "version": "1.0.0", "description": "Test API"},
            "components": {
                "schemas": {
                    "connectionStatus": {"type": "string", "enum": ["w", "n", "a"], "description": "Connection status"},
                    "delaySource": {"type": "string", "enum": ["L", "NA", "NM", "V", "IA", "IM", "A"], "description": "Delay source"}
                }
            }
        }
        self.loader = MasterdataLoader(str(self.data_dir), str(self.schema_dir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_schema_success_and_cache(self):
        schema = self.loader.load_schema()
        self.assertEqual(schema["title"], "Test Schema")
        schema2 = self.loader.load_schema()
        self.assertIs(schema, schema2)

    def test_load_schema_file_not_found(self):
        os.remove(self.schema_dir / "timetables.schema.json")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_schema()
        self.assertIn("Schema file not found", str(cm.exception))

    def test_load_schema_invalid_json(self):
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            f.write("invalid json {")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_schema()
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_load_masterdata_success(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        y = self.data_dir / "test.yaml"
        with open(y, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        md = self.loader.load_timetable_masterdata("test.yaml")
        self.assertEqual(md.info.title, "Test Timetables")
        self.assertEqual(md.info.version, "1.0.0")
        self.assertIsNotNone(md.data_hash)

    def test_load_masterdata_file_not_found(self):
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("nonexistent.yaml")
        self.assertIn("Masterdata file not found", str(cm.exception))

    def test_load_masterdata_empty_file(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        y = self.data_dir / "empty.yaml"
        with open(y, 'w') as f:
            f.write("")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty.yaml")
        self.assertIn("empty or contains only null values", str(cm.exception))

    def test_load_masterdata_invalid_structure(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        y = self.data_dir / "invalid.yaml"
        with open(y, 'w') as f:
            yaml.dump(["this", "is", "a", "list"], f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid.yaml")
        self.assertIn("does not contain a valid object structure", str(cm.exception))

    def test_load_masterdata_invalid_yaml(self):
        y = self.data_dir / "invalid.yaml"
        with open(y, 'w') as f:
            f.write("invalid: yaml: [unclosed")
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid.yaml")
        self.assertIn("Invalid YAML syntax", str(cm.exception))

    def test_load_masterdata_schema_validation_failure(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid = {"openapi": "3.0.1"}
        y = self.data_dir / "invalid_schema.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_schema.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))

    def test_load_masterdata_missing_title(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid = {"openapi": "3.0.1", "info": {"version": "1.0.0"}, "components": {"schemas": {}}}
        y = self.data_dir / "no_title.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("no_title.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))
        self.assertIn("'title' is a required property", str(cm.exception))

    def test_load_masterdata_missing_version(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid = {"openapi": "3.0.1", "info": {"title": "Test"}, "components": {"schemas": {}}}
        y = self.data_dir / "no_version.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("no_version.yaml")
        self.assertIn("Schema validation failed", str(cm.exception))
        self.assertIn("'version' is a required property", str(cm.exception))

    def test_load_masterdata_empty_title_custom_validation(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        # permissives Schema beibehalten
        with open(self.schema_dir / "timetables.schema.json", 'w') as f:
            json.dump(self.valid_schema, f)
        invalid = {"openapi": "3.0.1", "info": {"title": "", "version": "1.0.0"}, "components": {"schemas": {}}}
        y = self.data_dir / "empty_title.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty_title.yaml")
        self.assertIn("API title is missing or empty", str(cm.exception))

    def test_load_masterdata_empty_version_custom_validation(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid = {"openapi": "3.0.1", "info": {"title": "Test", "version": ""}, "components": {"schemas": {}}}
        y = self.data_dir / "empty_version.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("empty_version.yaml")
        self.assertIn("API version is missing or empty", str(cm.exception))

    def test_load_masterdata_invalid_connection_status_schema(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid_data = dict(self.valid_yaml_data)
        invalid_data["components"] = {"schemas": {
            "connectionStatus": {"type": "string", "enum": ["w", "n"]},
            "delaySource": self.valid_yaml_data["components"]["schemas"]["delaySource"]
        }}
        y = self.data_dir / "invalid_enum.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid_data, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_enum.yaml")
        self.assertIn("Connection status schema is missing expected values", str(cm.exception))

    def test_load_masterdata_invalid_delay_source_schema(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        invalid_data = dict(self.valid_yaml_data)
        invalid_data["components"] = {"schemas": {
            "connectionStatus": self.valid_yaml_data["components"]["schemas"]["connectionStatus"],
            "delaySource": {"type": "string", "enum": ["L", "NA"]}
        }}
        y = self.data_dir / "invalid_delay.yaml"
        with open(y, 'w') as f:
            yaml.dump(invalid_data, f)
        with self.assertRaises(MasterdataValidationError) as cm:
            self.loader.load_timetable_masterdata("invalid_delay.yaml")
        self.assertIn("Delay source schema is missing expected values", str(cm.exception))

    def test_cache_and_reload(self):
        if yaml is None:
            self.skipTest("PyYAML not available")
        y = self.data_dir / "test.yaml"
        with open(y, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        md1 = self.loader.load_timetable_masterdata("test.yaml")
        cached = self.loader.get_cached_masterdata()
        self.assertIs(md1, cached)
        md2 = self.loader.reload_masterdata("test.yaml")
        self.assertIsNot(md1, md2)
        self.assertEqual(md1.info.title, md2.info.title)

    def test_validate_connection_data_paths(self):
        errors = self.loader.validate_connection_data({"cs": "w"})
        self.assertIn("loader", errors)
        self.assertIn("No masterdata loaded", errors["loader"])
        if yaml is None:
            self.skipTest("PyYAML not available")
        y = self.data_dir / "test.yaml"
        with open(y, 'w') as f:
            yaml.dump(self.valid_yaml_data, f)
        self.loader.load_timetable_masterdata("test.yaml")
        ok_errors = self.loader.validate_connection_data({"cs": "w", "eva": 8000261, "ts": "2404011437"})
        self.assertEqual(len(ok_errors), 0)
        bad_errors = self.loader.validate_connection_data({"cs": "invalid", "eva": "not_a_number", "ts": "short"})
        self.assertIn("cs", bad_errors)
        self.assertIn("eva", bad_errors)
        self.assertIn("ts", bad_errors)

    def test_global_function_wrapper(self):
        # Patch global loader in masterdata_loader Modul
        import masterdata_loader as mdl
        class _Dummy:
            def load_timetable_masterdata(self, fn):
                return TimetableMasterdata(openapi_version="3.0.1", info=ApiInfo(title="Test", version="1.0.0"), data_hash="x")
        original = mdl._global_loader
        mdl._global_loader = _Dummy()
        try:
            res = load_timetable_masterdata_global("test.yaml")
            self.assertIsInstance(res, TimetableMasterdata)
            self.assertEqual(res.info.title, "Test")
        finally:
            mdl._global_loader = original


if __name__ == "__main__":
    unittest.main()
