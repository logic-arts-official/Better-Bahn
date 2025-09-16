#!/usr/bin/env python3
"""
Property-based tests for Better-Bahn functionality.

Uses Hypothesis to generate random test data and verify system invariants.
"""

import unittest
import yaml
import tempfile
import os
from hypothesis import given, strategies as st, settings, example
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle
from unittest.mock import patch, mock_open

# Import functions under test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import (
    load_timetable_masterdata, 
    validate_eva_number, 
    create_traveller_payload,
    enhance_connection_with_real_time
)


class TestPropertyBasedTesting(unittest.TestCase):
    """Property-based tests using Hypothesis."""

    @given(st.integers(min_value=1000000, max_value=9999999))
    def test_eva_number_validation_property(self, eva_number):
        """Property: All 7-digit numbers should be valid EVA numbers."""
        self.assertTrue(validate_eva_number(eva_number))
        self.assertTrue(validate_eva_number(str(eva_number)))

    @given(st.integers().filter(lambda x: x < 1000000 or x > 9999999))
    def test_eva_number_invalid_property(self, invalid_eva):
        """Property: All numbers outside 7-digit range should be invalid."""
        self.assertFalse(validate_eva_number(invalid_eva))

    @given(st.text().filter(lambda x: not x.isdigit() or len(x) != 7))
    def test_eva_number_invalid_text_property(self, invalid_text):
        """Property: All non-7-digit-numeric text should be invalid."""
        self.assertFalse(validate_eva_number(invalid_text))

    @given(st.integers(min_value=1, max_value=120), 
           st.sampled_from(['BC25_1', 'BC25_2', 'BC50_1', 'BC50_2', None]))
    def test_traveller_payload_structure_property(self, age, bahncard):
        """Property: Traveller payload should always have consistent structure."""
        payload = create_traveller_payload(age, bahncard)
        
        # Invariants that should always hold
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 1)
        
        traveller = payload[0]
        self.assertIn('typ', traveller)
        self.assertIn('ermaessigungen', traveller)
        self.assertIn('anzahl', traveller)
        self.assertIn('alter', traveller)
        
        self.assertEqual(traveller['typ'], 'ERWACHSENER')
        self.assertEqual(traveller['anzahl'], 1)
        self.assertIsInstance(traveller['ermaessigungen'], list)
        self.assertEqual(len(traveller['ermaessigungen']), 1)

    @given(st.dictionaries(
        st.text(min_size=1), 
        st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
        min_size=1, 
        max_size=10
    ))
    def test_enhance_connection_preserves_data_property(self, connection_data):
        """Property: Enhancement should preserve original data structure."""
        # Add required verbindungen structure for testing
        test_data = {
            'verbindungen': [{}],
            **connection_data
        }
        
        enhanced = enhance_connection_with_real_time(test_data, None)
        
        # Original keys should be preserved
        for key in connection_data:
            self.assertIn(key, enhanced)
            self.assertEqual(enhanced[key], connection_data[key])

    @given(st.text(min_size=1, max_size=1000))
    def test_yaml_loading_error_handling_property(self, yaml_content):
        """Property: YAML loading should handle any text input gracefully."""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                # Should never raise an exception, always return None or valid data
                try:
                    result = load_timetable_masterdata()
                    # Result should be None or a dictionary
                    self.assertTrue(result is None or isinstance(result, dict))
                except Exception as e:
                    self.fail(f"YAML loading should handle all text gracefully, but raised: {e}")


class TimetableRoundTripStateMachine(RuleBasedStateMachine):
    """Stateful testing for timetable data round-trip invariants."""
    
    yaml_content = Bundle('yaml_content')
    
    @rule(target=yaml_content, 
          version=st.text(min_size=1, max_size=20),
          stations=st.lists(
              st.dictionaries(
                  st.text(min_size=1, max_size=20),
                  st.one_of(st.text(), st.integers()),
                  min_size=1, max_size=5
              ),
              min_size=1, max_size=10
          ))
    def generate_valid_yaml(self, version, stations):
        """Generate valid YAML content."""
        content = {
            'info': {'version': version},
            'components': {
                'schemas': {
                    'station': {
                        'type': 'object',
                        'properties': stations[0] if stations else {}
                    }
                }
            },
            'stations': stations
        }
        return content
    
    @rule(content=yaml_content)
    def yaml_round_trip_preserves_structure(self, content):
        """Test that YAML round-trip preserves essential structure."""
        # Convert to YAML string and back
        yaml_str = yaml.dump(content)
        
        with patch('builtins.open', mock_open(read_data=yaml_str)):
            with patch('os.path.join', return_value='mocked_path'):
                loaded = load_timetable_masterdata()
                
                if loaded is not None:
                    # Essential structure should be preserved
                    if 'info' in content:
                        assert 'info' in loaded, f"'info' key missing in loaded data. Content: {content}, Loaded: {loaded}"
                    if 'components' in content:
                        assert 'components' in loaded, f"'components' key missing in loaded data"

    @invariant()
    def yaml_content_bundle_not_empty(self):
        """Invariant: We should always have some YAML content to test."""
        # This is automatically maintained by Hypothesis
        pass


class TestYAMLPerformance(unittest.TestCase):
    """Tests for YAML parsing performance and benchmarking."""

    def test_yaml_parsing_small_file(self):
        """Test YAML parsing performance with small files."""
        small_yaml = {
            'info': {'version': '1.0'},
            'components': {'schemas': {'test': 'data'}}
        }
        yaml_content = yaml.dump(small_yaml)
        
        import time
        start_time = time.time()
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        end_time = time.time()
        parse_time = end_time - start_time
        
        # Small files should parse very quickly (under 1 second)
        self.assertLess(parse_time, 1.0)
        self.assertIsNotNone(result)

    def test_yaml_parsing_medium_file(self):
        """Test YAML parsing performance with medium-sized files."""
        # Generate a medium-sized YAML structure
        medium_yaml = {
            'info': {'version': '1.0.213'},
            'components': {
                'schemas': {
                    f'schema_{i}': {
                        'type': 'object',
                        'properties': {
                            f'prop_{j}': {'type': 'string'}
                            for j in range(10)
                        }
                    }
                    for i in range(50)
                }
            }
        }
        yaml_content = yaml.dump(medium_yaml)
        
        import time
        start_time = time.time()
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        end_time = time.time()
        parse_time = end_time - start_time
        
        # Medium files should still parse reasonably quickly (under 5 seconds)
        self.assertLess(parse_time, 5.0)
        self.assertIsNotNone(result)

    @given(st.integers(min_value=1, max_value=100))
    def test_yaml_parsing_scales_linearly(self, schema_count):
        """Property: YAML parsing time should scale roughly linearly with content size."""
        # Generate YAML with variable number of schemas
        yaml_data = {
            'info': {'version': '1.0'},
            'components': {
                'schemas': {
                    f'schema_{i}': {'type': 'object'}
                    for i in range(schema_count)
                }
            }
        }
        yaml_content = yaml.dump(yaml_data)
        
        import time
        start_time = time.time()
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        end_time = time.time()
        parse_time = end_time - start_time
        
        # Parse time should be reasonable even for larger content
        # Use a generous upper bound that scales with content size
        max_expected_time = 0.1 + (schema_count * 0.01)  # Base time + linear scaling
        self.assertLess(parse_time, max_expected_time)
        
        # Should still successfully parse
        self.assertIsNotNone(result)


class TestInputValidationProperties(unittest.TestCase):
    """Property-based tests for input validation and fuzzing."""

    @given(st.one_of(st.none(), st.text(), st.integers(), st.floats(), st.lists(st.text())))
    def test_eva_validation_handles_any_input(self, arbitrary_input):
        """Property: EVA validation should handle any input type without crashing."""
        try:
            result = validate_eva_number(arbitrary_input)
            # Should always return a boolean
            self.assertIsInstance(result, bool)
        except Exception as e:
            self.fail(f"EVA validation should handle any input, but raised: {e}")

    @given(st.dictionaries(
        st.text(min_size=1),
        st.recursive(
            st.one_of(st.none(), st.booleans(), st.integers(), st.floats(), st.text()),
            lambda children: st.one_of(st.lists(children), st.dictionaries(st.text(), children)),
            max_leaves=50
        ),
        min_size=0,
        max_size=20
    ))
    def test_enhance_connection_with_arbitrary_data(self, arbitrary_data):
        """Property: Connection enhancement should handle arbitrary nested data."""
        try:
            result = enhance_connection_with_real_time(arbitrary_data, None)
            # Should return the same type as input or None
            if arbitrary_data is None:
                self.assertIsNone(result)
            else:
                self.assertIsInstance(result, type(arbitrary_data))
        except Exception as e:
            self.fail(f"Connection enhancement should handle arbitrary data, but raised: {e}")


# Create a test case for the stateful machine
TestTimetableRoundTrip = TimetableRoundTripStateMachine.TestCase


if __name__ == '__main__':
    # Configure Hypothesis settings for faster test execution in CI
    settings.register_profile("ci", max_examples=20, deadline=1000)
    settings.register_profile("dev", max_examples=100, deadline=2000)
    
    # Use CI profile by default
    settings.load_profile("ci")
    
    unittest.main()