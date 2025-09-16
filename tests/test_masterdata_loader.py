#!/usr/bin/env python3
"""
Unit tests for masterdata loading functionality.

Tests malformed YAML handling, file not found scenarios, and proper loading behavior.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, mock_open
import yaml

# Import functions under test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import load_timetable_masterdata, get_station_schema, validate_eva_number


class TestMasterdataLoader(unittest.TestCase):
    """Test cases for masterdata loading functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_yaml_content = {
            'info': {'version': '1.0.213'},
            'components': {
                'schemas': {
                    'station': {
                        'type': 'object',
                        'properties': {
                            'eva': {'type': 'integer', 'format': 'int64'}
                        }
                    }
                }
            }
        }
        
        self.valid_yaml_str = yaml.dump(self.valid_yaml_content)

    def test_load_timetable_masterdata_success(self):
        """Test successful loading of valid YAML masterdata."""
        with patch('builtins.open', mock_open(read_data=self.valid_yaml_str)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        self.assertIsNotNone(result)
        self.assertEqual(result['info']['version'], '1.0.213')
        self.assertIn('components', result)
        self.assertIn('schemas', result['components'])

    def test_load_timetable_masterdata_file_not_found(self):
        """Test graceful handling when YAML file is not found."""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            result = load_timetable_masterdata()
            
        self.assertIsNone(result)

    def test_load_timetable_masterdata_malformed_yaml(self):
        """Test that malformed YAML raises appropriate exception handling."""
        malformed_yaml = "invalid: yaml: content: [unclosed bracket"
        
        with patch('builtins.open', mock_open(read_data=malformed_yaml)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        # Should return None when YAML is malformed
        self.assertIsNone(result)

    def test_load_timetable_masterdata_yaml_scanner_error(self):
        """Test handling of YAML scanner errors."""
        yaml_with_tabs = "info:\n\tversion: 1.0.213"  # Tabs cause YAML scanner errors
        
        with patch('builtins.open', mock_open(read_data=yaml_with_tabs)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        self.assertIsNone(result)

    def test_load_timetable_masterdata_unexpected_error(self):
        """Test handling of unexpected errors during loading."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = load_timetable_masterdata()
            
        self.assertIsNone(result)

    def test_get_station_schema_with_valid_masterdata(self):
        """Test schema extraction from valid masterdata."""
        with patch('main.load_timetable_masterdata', return_value=self.valid_yaml_content):
            schema = get_station_schema()
            
        self.assertIsNotNone(schema)
        self.assertIn('station', schema)

    def test_get_station_schema_with_no_masterdata(self):
        """Test schema extraction when masterdata is unavailable."""
        with patch('main.load_timetable_masterdata', return_value=None):
            schema = get_station_schema()
            
        self.assertIsNone(schema)

    def test_get_station_schema_with_incomplete_masterdata(self):
        """Test schema extraction with incomplete masterdata structure."""
        incomplete_data = {'info': {'version': '1.0.213'}}  # Missing components
        
        with patch('main.load_timetable_masterdata', return_value=incomplete_data):
            schema = get_station_schema()
            
        self.assertIsNone(schema)

    def test_validate_eva_number_valid_numbers(self):
        """Test EVA number validation with valid inputs."""
        valid_numbers = [
            1000000,
            8000261,  # München Hbf
            8011160,  # Berlin Hbf
            9999999,
            "1000000",
            "8000261"
        ]
        
        for eva_no in valid_numbers:
            with self.subTest(eva_no=eva_no):
                self.assertTrue(validate_eva_number(eva_no))

    def test_validate_eva_number_invalid_numbers(self):
        """Test EVA number validation with invalid inputs."""
        invalid_numbers = [
            999999,    # Too small
            10000000,  # Too large
            "abc123",  # Non-numeric
            None,      # None value
            [],        # Wrong type
            {},        # Wrong type
            "",        # Empty string
            "123abc",  # Mixed characters
            -1000000   # Negative
        ]
        
        for eva_no in invalid_numbers:
            with self.subTest(eva_no=eva_no):
                self.assertFalse(validate_eva_number(eva_no))

    def test_validate_eva_number_edge_cases(self):
        """Test EVA number validation edge cases."""
        # Test boundary values
        self.assertTrue(validate_eva_number(1000000))   # Lower bound
        self.assertTrue(validate_eva_number(9999999))   # Upper bound
        self.assertFalse(validate_eva_number(999999))   # Just below lower bound
        self.assertFalse(validate_eva_number(10000000)) # Just above upper bound
        
        # Test type conversion
        self.assertTrue(validate_eva_number("1000000"))
        self.assertFalse(validate_eva_number("1000000.0"))  # Float string


class TestMasterdataErrorHandling(unittest.TestCase):
    """Test error handling scenarios for masterdata operations."""

    def test_yaml_load_with_circular_reference(self):
        """Test handling of YAML with circular references."""
        # This would normally cause infinite recursion
        yaml_content = """
        reference: &ref
          self: *ref
        """
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        # Should handle gracefully and return None or valid data
        # yaml.safe_load should handle this case
        self.assertIsNotNone(result)  # safe_load handles circular refs

    def test_yaml_load_with_large_file(self):
        """Test behavior with very large YAML files."""
        # Simulate memory constraint scenario
        with patch('yaml.safe_load', side_effect=MemoryError("Out of memory")):
            with patch('builtins.open', mock_open(read_data="test: data")):
                with patch('os.path.join', return_value='mocked_path'):
                    result = load_timetable_masterdata()
                    
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()