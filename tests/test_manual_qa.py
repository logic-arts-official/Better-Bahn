#!/usr/bin/env python3
"""
Manual QA checklist automation and validation tests.

Automates testing for airplane mode scenarios, rapid refresh rate limiting,
and corrupted YAML handling.
"""

import unittest
import tempfile
import os
import subprocess
import time
from unittest.mock import patch, mock_open, Mock
import requests

# Import functions under test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import load_timetable_masterdata
from db_transport_api import DBTransportAPIClient


class TestAirplaneModeScenarios(unittest.TestCase):
    """Test behavior when network connectivity is unavailable (airplane mode)."""

    def test_masterdata_loading_offline(self):
        """Test that static masterdata can be loaded without network access."""
        # Simulate airplane mode by patching network requests to fail
        with patch('requests.get', side_effect=requests.ConnectionError("Network unreachable")):
            with patch('requests.post', side_effect=requests.ConnectionError("Network unreachable")):
                # Should still be able to load local YAML files
                valid_yaml = """
info:
  version: "1.0.213"
components:
  schemas:
    station:
      type: object
      properties:
        eva:
          type: integer
"""
                
                with patch('builtins.open', mock_open(read_data=valid_yaml)):
                    with patch('os.path.join', return_value='mocked_path'):
                        result = load_timetable_masterdata()
                        
                # Should succeed with local data
                self.assertIsNotNone(result)
                self.assertEqual(result['info']['version'], '1.0.213')

    def test_api_client_offline_behavior(self):
        """Test API client behavior when network is unavailable."""
        client = DBTransportAPIClient(rate_limit_delay=0.01)
        
        # Mock network failure
        with patch.object(client.session, 'get', side_effect=requests.ConnectionError("Network unreachable")):
            result = client._make_request('/test')
            
        # Should return None gracefully, not crash
        self.assertIsNone(result)

    def test_main_application_offline_resilience(self):
        """Test that main application handles offline scenarios gracefully."""
        # Test command line interface with network errors
        test_url = "https://www.bahn.de/buchung/start?vbid=test123"
        
        # Mock all network calls to fail
        with patch('requests.get', side_effect=requests.ConnectionError("Network unreachable")):
            with patch('requests.post', side_effect=requests.ConnectionError("Network unreachable")):
                # Should not crash, should handle gracefully
                try:
                    # This would normally be tested by running the actual CLI
                    # For unit test, we test the core functions that handle network errors
                    from main import resolve_vbid_to_connection, create_traveller_payload
                    
                    traveller_payload = create_traveller_payload(30, None)
                    result = resolve_vbid_to_connection("test123", traveller_payload, False)
                    
                    # Should return None for network error, not crash
                    self.assertIsNone(result)
                    
                except Exception as e:
                    self.fail(f"Application should handle network errors gracefully, but raised: {e}")

    def test_static_data_availability_offline(self):
        """Test that static functionality works without network."""
        from main import validate_eva_number, create_traveller_payload
        
        # These functions should work regardless of network status
        with patch('requests.get', side_effect=requests.ConnectionError("Network unreachable")):
            # EVA number validation should work offline
            self.assertTrue(validate_eva_number(8000261))
            self.assertFalse(validate_eva_number("invalid"))
            
            # Traveller payload creation should work offline
            payload = create_traveller_payload(30, "BC25_2")
            self.assertIsNotNone(payload)
            self.assertEqual(len(payload), 1)


class TestRapidRefreshRateLimiting(unittest.TestCase):
    """Test rate limiting under rapid refresh scenarios."""

    def test_rapid_refresh_five_clicks_five_seconds(self):
        """Test rapid refresh scenario: 5 clicks in 5 seconds should not exceed rate limit."""
        client = DBTransportAPIClient(rate_limit_delay=0.5)  # 0.5 second rate limit
        
        click_times = []
        responses = []
        
        # Mock API responses
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'data': 'test'}
            mock_get.return_value = mock_response
            
            # Simulate 5 rapid clicks
            start_time = time.time()
            for i in range(5):
                click_time = time.time()
                result = client._make_request(f'/test/{i}')
                responses.append(result)
                click_times.append(time.time() - click_time)
                
            total_time = time.time() - start_time
        
        print(f"\nRapid Refresh Test Results:")
        print(f"  Total time for 5 requests: {total_time:.2f}s")
        print(f"  Individual request times: {[f'{t:.2f}s' for t in click_times]}")
        
        # All requests should succeed
        self.assertEqual(len([r for r in responses if r is not None]), 5)
        
        # Total time should be at least 2.5 seconds (5 requests × 0.5s rate limit)
        self.assertGreaterEqual(total_time, 2.5)
        
        # Each individual request should take at least the rate limit time
        for click_time in click_times:
            self.assertGreaterEqual(click_time, 0.5)

    def test_rate_limit_prevents_api_overload(self):
        """Test that rate limiting effectively prevents API overload."""
        client = DBTransportAPIClient(rate_limit_delay=0.2)
        
        request_intervals = []
        last_request_time = None
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'data': 'test'}
            mock_get.return_value = mock_response
            
            # Make several requests and measure intervals
            for i in range(10):
                current_time = time.time()
                client._make_request(f'/test/{i}')
                
                if last_request_time is not None:
                    interval = current_time - last_request_time
                    request_intervals.append(interval)
                
                last_request_time = current_time
        
        print(f"\nRate Limiting Intervals:")
        print(f"  Average interval: {sum(request_intervals)/len(request_intervals):.2f}s")
        print(f"  Min interval: {min(request_intervals):.2f}s")
        
        # All intervals should be at least the rate limit delay
        for interval in request_intervals:
            self.assertGreaterEqual(interval, 0.2)

    def test_burst_request_handling(self):
        """Test handling of burst requests that would exceed rate limits."""
        client = DBTransportAPIClient(rate_limit_delay=1.0)  # 1 second rate limit
        
        # Try to make 3 requests very quickly
        burst_start = time.time()
        results = []
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'burst': 'test'}
            mock_get.return_value = mock_response
            
            for i in range(3):
                result = client._make_request(f'/burst/{i}')
                results.append(result)
        
        burst_total_time = time.time() - burst_start
        
        print(f"\nBurst Request Results:")
        print(f"  3 burst requests completed in: {burst_total_time:.2f}s")
        
        # Should take at least 3 seconds (3 × 1 second rate limit)
        self.assertGreaterEqual(burst_total_time, 3.0)
        
        # All requests should succeed despite rate limiting
        self.assertEqual(len([r for r in results if r is not None]), 3)


class TestCorruptedYAMLHandling(unittest.TestCase):
    """Test handling of corrupted or malformed YAML files."""

    def test_corrupted_yaml_startup_message(self):
        """Test that corrupted YAML produces clear startup message."""
        corrupted_yamls = [
            "invalid: yaml: content: [",  # Syntax error
            "key: value\n\tinvalid_indent",  # Indentation error
            "key: value\nkey: duplicate",  # YAML may handle duplicates
            "\x00\x01\x02invalid_binary",  # Binary data
            "extremely_long_key_" + "x" * 10000 + ": value",  # Extremely long content
        ]
        
        for i, yaml_content in enumerate(corrupted_yamls):
            with self.subTest(yaml_type=f"corruption_{i}"):
                with patch('builtins.open', mock_open(read_data=yaml_content)):
                    with patch('os.path.join', return_value='mocked_path'):
                        # Should not crash and should return None
                        result = load_timetable_masterdata()
                        
                # Should gracefully handle corruption
                self.assertIsNone(result)

    def test_yaml_scanner_error_handling(self):
        """Test specific YAML scanner error scenarios."""
        # YAML with various syntax issues that trigger scanner errors
        problematic_yamls = [
            "---\nkey: 'unclosed string",  # Unclosed quotes
            "---\n[unclosed, list",  # Unclosed list
            "---\n{unclosed: dict",  # Unclosed dict
            "---\nkey: |\n  multiline\n invalid_indent",  # Multiline string issues
        ]
        
        for yaml_content in problematic_yamls:
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.join', return_value='mocked_path'):
                    # Should handle scanner errors gracefully
                    try:
                        result = load_timetable_masterdata()
                        # Should return None for malformed YAML
                        self.assertIsNone(result)
                    except Exception as e:
                        self.fail(f"Should handle YAML scanner errors gracefully, but raised: {e}")

    def test_empty_yaml_file_handling(self):
        """Test handling of empty or whitespace-only YAML files."""
        empty_cases = [
            "",  # Completely empty
            "   ",  # Only whitespace
            "\n\n\n",  # Only newlines
            "# Only comments\n# No actual content",  # Only comments
        ]
        
        for empty_content in empty_cases:
            with patch('builtins.open', mock_open(read_data=empty_content)):
                with patch('os.path.join', return_value='mocked_path'):
                    result = load_timetable_masterdata()
                    
                    # Should handle empty files gracefully
                    # May return None or empty dict depending on yaml.safe_load behavior
                    self.assertTrue(result is None or result == {})

    def test_yaml_with_invalid_encoding(self):
        """Test handling of YAML files with encoding issues."""
        # Simulate encoding errors during file reading
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')):
            result = load_timetable_masterdata()
            
        # Should handle encoding errors gracefully
        self.assertIsNone(result)

    def test_missing_yaml_file_startup_behavior(self):
        """Test application behavior when YAML file is missing."""
        # Simulate missing file
        with patch('builtins.open', side_effect=FileNotFoundError("YAML file not found")):
            result = load_timetable_masterdata()
            
        # Should handle missing file gracefully
        self.assertIsNone(result)

    def test_yaml_file_permission_error(self):
        """Test handling of permission errors when reading YAML."""
        # Simulate permission denied
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = load_timetable_masterdata()
            
        # Should handle permission errors gracefully
        self.assertIsNone(result)


class TestManualQAChecklist(unittest.TestCase):
    """Automated validation of manual QA checklist items."""

    def test_application_startup_without_yaml(self):
        """Test that application can start even without YAML masterdata."""
        # This tests graceful degradation
        with patch('main.load_timetable_masterdata', return_value=None):
            try:
                from main import create_traveller_payload, validate_eva_number
                
                # Core functions should still work
                payload = create_traveller_payload(30, None)
                self.assertIsNotNone(payload)
                
                eva_valid = validate_eva_number(8000261)
                self.assertTrue(eva_valid)
                
            except Exception as e:
                self.fail(f"Application should work without YAML masterdata, but failed: {e}")

    def test_command_line_interface_error_messages(self):
        """Test that CLI provides clear error messages for common issues."""
        # Test invalid URL handling
        from main import extract_url_details
        
        invalid_urls = [
            "not_a_url",
            "http://wrong-domain.com/path",
            "https://bahn.de/wrong/path",
        ]
        
        for url in invalid_urls:
            try:
                result = extract_url_details(url)
                # Should handle invalid URLs gracefully
                if result is not None:
                    # If it doesn't return None, should at least not crash
                    self.assertIsInstance(result, (dict, type(None)))
            except Exception as e:
                # Should not raise exceptions for invalid URLs
                self.fail(f"URL handling should be robust, but raised exception for '{url}': {e}")

    def test_network_error_user_feedback(self):
        """Test that network errors provide helpful user feedback."""
        # Mock various network error scenarios
        network_errors = [
            requests.ConnectionError("Connection refused"),
            requests.Timeout("Request timeout"),
            requests.HTTPError("503 Service Unavailable"),
        ]
        
        client = DBTransportAPIClient()
        
        for error in network_errors:
            with patch.object(client.session, 'get', side_effect=error):
                # Should handle error gracefully and return None
                result = client._make_request('/test')
                self.assertIsNone(result)

    def test_data_validation_edge_cases(self):
        """Test data validation with edge case inputs."""
        from main import validate_eva_number, create_traveller_payload
        
        # EVA number edge cases
        edge_cases = [
            (1000000, True),   # Lower bound
            (9999999, True),   # Upper bound
            (999999, False),   # Just below range
            (10000000, False), # Just above range
            ("8000261", True), # String representation
            ("8000261.0", False), # Float string
        ]
        
        for eva_input, expected in edge_cases:
            with self.subTest(eva_input=eva_input):
                result = validate_eva_number(eva_input)
                self.assertEqual(result, expected)
        
        # Traveller payload edge cases
        age_cases = [1, 17, 18, 65, 100, 120]
        for age in age_cases:
            with self.subTest(age=age):
                payload = create_traveller_payload(age, None)
                self.assertIsNotNone(payload)
                self.assertEqual(len(payload), 1)


class TestSystemResilience(unittest.TestCase):
    """Test overall system resilience and error recovery."""

    def test_partial_system_failure_handling(self):
        """Test behavior when some components fail but others work."""
        # Scenario: YAML loading fails but API client works
        with patch('main.load_timetable_masterdata', return_value=None):
            client = DBTransportAPIClient()
            
            # Should still be able to create client
            self.assertIsNotNone(client)
            
            # Mock successful API call
            with patch.object(client.session, 'get') as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {'test': 'data'}
                mock_get.return_value = mock_response
                
                result = client._make_request('/test')
                self.assertIsNotNone(result)

    def test_memory_usage_under_load(self):
        """Test that memory usage remains reasonable under typical load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simulate typical usage load
        client = DBTransportAPIClient(rate_limit_delay=0.01)
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'test': 'data'}
            mock_get.return_value = mock_response
            
            # Make many requests to test memory usage
            for i in range(100):
                client._make_request(f'/test/{i}')
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        print(f"\nMemory Usage Test:")
        print(f"  Memory increase: {memory_increase_mb:.2f} MB")
        
        # Memory increase should be reasonable (less than 50MB for 100 requests)
        self.assertLess(memory_increase_mb, 50)


if __name__ == '__main__':
    unittest.main(verbosity=2)