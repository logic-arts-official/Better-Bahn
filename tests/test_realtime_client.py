#!/usr/bin/env python3
"""
Unit tests for realtime client functionality.

Tests 429 rate limiting scenarios, backoff mechanisms, and error handling.
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import HTTPError, RequestException

# Import functions under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_transport_api import DBTransportAPIClient


class TestRealtimeClient(unittest.TestCase):
    """Test cases for realtime API client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = DBTransportAPIClient(rate_limit_delay=0.01)  # Faster for testing

    def test_init_with_default_rate_limit(self):
        """Test client initialization with default rate limit."""
        client = DBTransportAPIClient()
        self.assertEqual(client.rate_limit_delay, 0.2)
        self.assertIsNotNone(client.session)

    def test_init_with_custom_rate_limit(self):
        """Test client initialization with custom rate limit."""
        client = DBTransportAPIClient(rate_limit_delay=1.0)
        self.assertEqual(client.rate_limit_delay, 1.0)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_success(self, mock_get, mock_sleep):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response

        result = self.client._make_request('/test')

        self.assertEqual(result, {'test': 'data'})
        mock_sleep.assert_called_once_with(0.01)
        mock_get.assert_called_once()

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_429_rate_limit_error(self, mock_get, mock_sleep):
        """Test 429 rate limiting error handling."""
        # Mock 429 response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = self.client._make_request('/test')

        # Should return None on 429 error
        self.assertIsNone(result)
        mock_sleep.assert_called_once_with(0.01)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_network_error(self, mock_get, mock_sleep):
        """Test network error handling."""
        # Mock network error
        mock_get.side_effect = requests.ConnectionError("Network error")

        result = self.client._make_request('/test')

        self.assertIsNone(result)
        mock_sleep.assert_called_once_with(0.01)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_timeout_error(self, mock_get, mock_sleep):
        """Test timeout error handling."""
        # Mock timeout error
        mock_get.side_effect = requests.Timeout("Request timeout")

        result = self.client._make_request('/test')

        self.assertIsNone(result)
        mock_sleep.assert_called_once_with(0.01)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_with_params(self, mock_get, mock_sleep):
        """Test API request with query parameters."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'locations': []}
        mock_get.return_value = mock_response

        params = {'query': 'Berlin', 'results': 5}
        result = self.client._make_request('/locations', params)

        self.assertEqual(result, {'locations': []})
        mock_get.assert_called_once_with(
            f"{self.client.BASE_URL}/locations",
            params=params,
            timeout=30
        )

    @patch('db_transport_api.DBTransportAPIClient._make_request')
    def test_find_locations_success(self, mock_make_request):
        """Test successful location search."""
        mock_make_request.return_value = [
            {'id': '8011160', 'name': 'Berlin Hbf', 'type': 'station'}
        ]

        result = self.client.find_locations('Berlin Hbf', results=1)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Berlin Hbf')
        mock_make_request.assert_called_once_with('/locations', {'query': 'Berlin Hbf', 'results': 1})

    @patch('db_transport_api.DBTransportAPIClient._make_request')
    def test_find_locations_no_results(self, mock_make_request):
        """Test location search with no results."""
        mock_make_request.return_value = None

        result = self.client.find_locations('NonexistentStation')

        self.assertIsNone(result)

    @patch('db_transport_api.DBTransportAPIClient._make_request')
    def test_get_journeys_success(self, mock_make_request):
        """Test successful journey search."""
        mock_make_request.return_value = {
            'journeys': [
                {
                    'legs': [
                        {'departure': '2024-01-01T10:00:00+01:00', 'arrival': '2024-01-01T12:00:00+01:00'}
                    ]
                }
            ]
        }

        result = self.client.get_journeys('8011160', '8000261')

        self.assertIsNotNone(result)
        self.assertIn('journeys', result)
        self.assertEqual(len(result['journeys']), 1)

    @patch('db_transport_api.DBTransportAPIClient._make_request')
    def test_get_journeys_no_results(self, mock_make_request):
        """Test journey search with no results."""
        mock_make_request.return_value = None

        result = self.client.get_journeys('8011160', '8000261')

        self.assertIsNone(result)


class TestRateLimitingBackoff(unittest.TestCase):
    """Test rate limiting and backoff scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = DBTransportAPIClient(rate_limit_delay=0.01)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_rate_limiting_delay_applied(self, mock_get, mock_sleep):
        """Test that rate limiting delay is properly applied."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response

        # Make multiple requests
        self.client._make_request('/test1')
        self.client._make_request('/test2')

        # Verify sleep was called for each request
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(0.01)

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_consecutive_429_errors(self, mock_get, mock_sleep):
        """Test handling of consecutive 429 errors."""
        # Mock consecutive 429 responses
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        # Make multiple requests that all fail with 429
        results = []
        for i in range(3):
            result = self.client._make_request(f'/test{i}')
            results.append(result)

        # All should return None
        self.assertTrue(all(result is None for result in results))
        self.assertEqual(mock_sleep.call_count, 3)

    def test_real_time_status_extraction(self):
        """Test real-time status extraction from journey data."""
        journey_data = {
            'legs': [
                {
                    'id': 'leg1',
                    'departure': {'delay': 300},  # 5 minutes in seconds
                    'arrival': {'delay': 300},
                    'cancelled': False
                },
                {
                    'id': 'leg2', 
                    'departure': {'delay': 600},  # 10 minutes in seconds
                    'arrival': {'delay': 600},
                    'cancelled': False
                }
            ]
        }

        status = self.client.get_real_time_status(journey_data)

        self.assertTrue(status['has_delays'])
        self.assertEqual(status['total_delay_minutes'], 15)
        self.assertEqual(status['cancelled_legs'], 0)

    def test_real_time_status_with_cancellations(self):
        """Test real-time status extraction with cancelled legs."""
        journey_data = {
            'legs': [
                {
                    'id': 'leg1',
                    'departure': {'delay': 0},
                    'arrival': {'delay': 0},
                    'cancelled': True
                },
                {
                    'id': 'leg2',
                    'departure': {'delay': 300},  # 5 minutes in seconds
                    'arrival': {'delay': 300},
                    'cancelled': False
                }
            ]
        }

        status = self.client.get_real_time_status(journey_data)

        self.assertTrue(status['has_delays'])
        self.assertEqual(status['total_delay_minutes'], 5)
        self.assertEqual(status['cancelled_legs'], 1)

    def test_real_time_status_no_delays(self):
        """Test real-time status extraction with no delays."""
        journey_data = {
            'legs': [
                {
                    'id': 'leg1',
                    'departure': {'delay': 0},
                    'arrival': {'delay': 0},
                    'cancelled': False
                }
            ]
        }

        status = self.client.get_real_time_status(journey_data)

        self.assertFalse(status['has_delays'])
        self.assertEqual(status['total_delay_minutes'], 0)
        self.assertEqual(status['cancelled_legs'], 0)

    def test_real_time_status_missing_data(self):
        """Test real-time status extraction with missing data."""
        journey_data = {'legs': []}

        status = self.client.get_real_time_status(journey_data)

        self.assertFalse(status['has_delays'])
        self.assertEqual(status['total_delay_minutes'], 0)
        self.assertEqual(status['cancelled_legs'], 0)


class TestClientErrorHandling(unittest.TestCase):
    """Test comprehensive error handling scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = DBTransportAPIClient(rate_limit_delay=0.01)

    @patch('requests.Session.get')
    def test_malformed_json_response(self, mock_get):
        """Test handling of malformed JSON responses."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = self.client._make_request('/test')

        self.assertIsNone(result)

    @patch('requests.Session.get')
    def test_http_error_codes(self, mock_get):
        """Test handling of various HTTP error codes."""
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503]
        
        for code in error_codes:
            with self.subTest(status_code=code):
                mock_response = Mock()
                http_error = HTTPError(f"{code} Error")
                http_error.response = Mock()
                http_error.response.status_code = code
                mock_response.raise_for_status.side_effect = http_error
                mock_get.return_value = mock_response

                result = self.client._make_request('/test')

                self.assertIsNone(result)

    @patch('requests.Session.get')
    def test_session_recovery(self, mock_get):
        """Test that session can recover after errors."""
        # First request fails
        mock_get.side_effect = [
            requests.ConnectionError("Network error"),
            Mock(raise_for_status=Mock(), json=Mock(return_value={'recovered': True}))
        ]

        # First request should fail
        result1 = self.client._make_request('/test')
        self.assertIsNone(result1)

        # Second request should succeed
        result2 = self.client._make_request('/test')
        self.assertEqual(result2, {'recovered': True})


if __name__ == '__main__':
    unittest.main()