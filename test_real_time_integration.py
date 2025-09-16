#!/usr/bin/env python3
"""
Comprehensive test matrix for Better-Bahn real-time API integration.
Tests various response scenarios including 200/429/500/timeout conditions.
"""

import sys
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from io import StringIO

# Local imports (assumes this test is part of a package; see README for setup)

from .better_bahn_config import BetterBahnConfig, APIConfig, CacheConfig, LoggingConfig
from .better_bahn_cache import CacheManager, MemoryCache, DiskCache
from .better_bahn_metrics import MetricsCollector
from .db_transport_api import DBTransportAPIClient, get_real_time_journey_info, Location


class TestAPIResponses(unittest.TestCase):
    """Test matrix for different API response scenarios"""
    
    def setUp(self):
        """Setup test configuration"""
        self.config = BetterBahnConfig(
            api=APIConfig(
                base_url="https://test.api.example.com",
                rate_limit_delay=0.01,  # Fast for testing
                max_retries=3,
                timeout=5
            ),
            cache=CacheConfig(
                enable_memory_cache=True,
                memory_cache_ttl=60,
                enable_disk_cache=False
            ),
            logging=LoggingConfig(
                enable_metrics=True,
                log_level="DEBUG"
            )
        )
        self.client = DBTransportAPIClient(self.config)
    
    def test_successful_response_200(self):
        """Test successful API response (200 OK)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "journeys": [
                {
                    "legs": [{"departure": {"delay": 0}, "arrival": {"delay": 0}}],
                    "duration": 3600
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNotNone(result)
            self.assertIn("journeys", result)
            self.assertEqual(len(result["journeys"]), 1)
    
    def test_rate_limit_response_429(self):
        """Test rate limiting response (429 Too Many Requests)"""
        # Mock rate limited response followed by success
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {'Retry-After': '2'}
        rate_limited_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=rate_limited_response)
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"journeys": []}
        success_response.raise_for_status.return_value = None
        
        with patch.object(self.client.session, 'get', side_effect=[rate_limited_response, success_response]):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNotNone(result)
            # Should have made 2 requests (rate limited, then success)
            self.assertEqual(self.client.session.get.call_count, 2)
    
    def test_exponential_backoff_on_rate_limit(self):
        """Test exponential backoff behavior without Retry-After header"""
        # Configure client without Retry-After respect
        config = BetterBahnConfig(
            api=APIConfig(
                respect_retry_after=False,
                exponential_backoff=True,
                rate_limit_delay=0.1,  # Larger delay for meaningful backoff
                max_retries=3
            )
        )
        client = DBTransportAPIClient(config)
        
        # Mock two rate limited responses, then success
        responses = []
        for i in range(2):
            response = Mock()
            response.status_code = 429
            response.headers = {}
            response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=response)
            responses.append(response)
        
        # Final success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"journeys": []}
        success_response.raise_for_status.return_value = None
        responses.append(success_response)
        
        with patch.object(client.session, 'get', side_effect=responses):
            start_time = time.time()
            result = client.get_journeys("Berlin Hbf", "München Hbf")
            elapsed = time.time() - start_time
            
            self.assertIsNotNone(result)
            # Should have taken some time due to exponential backoff
            self.assertGreater(elapsed, 0.1)
    
    def test_server_error_500(self):
        """Test server error response (500 Internal Server Error)"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNone(result)
            # Should have retried max_retries times
            self.assertEqual(self.client.session.get.call_count, self.config.api.max_retries)
    
    def test_timeout_error(self):
        """Test request timeout scenario"""
        with patch.object(self.client.session, 'get', side_effect=requests.exceptions.Timeout("Request timeout")):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNone(result)
            # Should have retried max_retries times
            self.assertEqual(self.client.session.get.call_count, self.config.api.max_retries)
    
    def test_connection_error(self):
        """Test connection error scenario"""
        with patch.object(self.client.session, 'get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNone(result)
            # Should have retried max_retries times
            self.assertEqual(self.client.session.get.call_count, self.config.api.max_retries)
    
    def test_client_error_400(self):
        """Test client error response (400 Bad Request)"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            
            self.assertIsNone(result)
            # Should NOT retry on client errors
            self.assertEqual(self.client.session.get.call_count, 1)


class TestCachingLayer(unittest.TestCase):
    """Test caching functionality"""
    
    def setUp(self):
        self.config = BetterBahnConfig(
            cache=CacheConfig(
                enable_memory_cache=True,
                memory_cache_ttl=2,  # Short TTL for testing
                enable_disk_cache=False
            )
        )
        self.client = DBTransportAPIClient(self.config)
    
    def test_cache_hit(self):
        """Test cache hit scenario"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"journeys": []}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            # First request - should hit API
            result1 = self.client.get_journeys("Berlin Hbf", "München Hbf")
            self.assertIsNotNone(result1)
            
            # Second request - should hit cache
            result2 = self.client.get_journeys("Berlin Hbf", "München Hbf")
            self.assertIsNotNone(result2)
            
            # Should only have made one API call
            self.assertEqual(self.client.session.get.call_count, 1)
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        # Test using _make_request directly with no cache_ttl override
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            # First request - should use memory cache TTL (2 seconds)
            result1 = self.client._make_request('/test', use_cache=True)
            self.assertIsNotNone(result1)
            
            # Wait for cache to expire
            time.sleep(3)
            
            # Second request - cache should be expired
            result2 = self.client._make_request('/test', use_cache=True)
            self.assertIsNotNone(result2)
            
            # Should have made two API calls
            self.assertEqual(self.client.session.get.call_count, 2)
    
    def test_cache_statistics(self):
        """Test cache statistics collection"""
        if self.client.cache_manager:
            stats = self.client.get_cache_stats()
            self.assertIsNotNone(stats)
            self.assertIn('memory_cache', stats)


class TestMetricsCollection(unittest.TestCase):
    """Test metrics and logging functionality"""
    
    def setUp(self):
        self.config = BetterBahnConfig(
            logging=LoggingConfig(
                enable_metrics=True,
                track_latency=True,
                track_status_codes=True,
                track_cache_hits=True
            )
        )
        self.client = DBTransportAPIClient(self.config)
    
    def test_metrics_collection(self):
        """Test that metrics are collected properly"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"journeys": []}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            self.assertIsNotNone(result)
            
            # Check metrics
            metrics = self.client.get_metrics()
            self.assertIsNotNone(metrics)
            self.assertIn('latency', metrics)
            self.assertIn('status_codes', metrics)
            self.assertIn('cache', metrics)
    
    def test_error_metrics(self):
        """Test error metrics collection"""
        with patch.object(self.client.session, 'get', side_effect=requests.exceptions.Timeout("Timeout")):
            result = self.client.get_journeys("Berlin Hbf", "München Hbf")
            self.assertIsNone(result)
            
            # Check error metrics
            metrics = self.client.get_metrics()
            self.assertIsNotNone(metrics)
            errors = metrics.get('errors', {})
            self.assertGreater(errors.get('total_errors', 0), 0)


class TestGracefulDegradation(unittest.TestCase):
    """Test graceful degradation scenarios"""
    
    def test_feature_flag_disabled(self):
        """Test behavior when real-time feature is disabled"""
        config = BetterBahnConfig(
            api=APIConfig(enable_realtime=False)
        )
        client = DBTransportAPIClient(config)
        
        result = client.get_journeys("Berlin Hbf", "München Hbf")
        self.assertIsNone(result)
    
    def test_high_level_function_fallback(self):
        """Test high-level function graceful degradation"""
        with patch('db_transport_api.DBTransportAPIClient') as mock_client_class:
            mock_client = Mock()
            mock_client.get_journeys.return_value = None
            mock_client.logger = Mock()
            mock_client_class.return_value = mock_client
            
            result = get_real_time_journey_info("Berlin Hbf", "München Hbf")
            
            self.assertIsNotNone(result)
            self.assertFalse(result['available'])
            self.assertEqual(result['journeys_count'], 0)


class TestConfigurationManagement(unittest.TestCase):
    """Test configuration management functionality"""
    
    def test_environment_configuration(self):
        """Test loading configuration from environment variables"""
        with patch.dict(os.environ, {
            'BETTER_BAHN_API_URL': 'https://custom.api.com',
            'BETTER_BAHN_TIMEOUT': '60',
            'BETTER_BAHN_RATE_LIMIT': '0.5',
            'BETTER_BAHN_ENABLE_REALTIME': 'false'
        }):
            config = BetterBahnConfig.from_env()
            
            self.assertEqual(config.api.base_url, 'https://custom.api.com')
            self.assertEqual(config.api.timeout, 60)
            self.assertEqual(config.api.rate_limit_delay, 0.5)
            self.assertFalse(config.api.enable_realtime)
    
    def test_file_configuration(self):
        """Test loading configuration from file"""
        config_data = {
            'api': {
                'base_url': 'https://file.api.com',
                'timeout': 45,
                'enable_realtime': True
            },
            'cache': {
                'enable_memory_cache': False,
                'enable_disk_cache': True
            }
        }
        
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = BetterBahnConfig.from_file(config_path)
            
            self.assertEqual(config.api.base_url, 'https://file.api.com')
            self.assertEqual(config.api.timeout, 45)
            self.assertTrue(config.api.enable_realtime)
            self.assertFalse(config.cache.enable_memory_cache)
            self.assertTrue(config.cache.enable_disk_cache)
        finally:
            os.unlink(config_path)


class TestIntegrationWithLiveAPI(unittest.TestCase):
    """Integration tests with live API (tagged/manual execution)"""
    
    @unittest.skipUnless(
        os.getenv('BETTER_BAHN_INTEGRATION_TESTS') == 'true',
        "Integration tests disabled (set BETTER_BAHN_INTEGRATION_TESTS=true to enable)"
    )
    def test_live_api_connectivity(self):
        """Test connectivity to live v6.db.transport.rest API"""
        client = DBTransportAPIClient()
        
        # Test if API is available
        is_available = client.is_available()
        
        if is_available:
            # Test location search
            locations = client.find_locations("Berlin Hbf", results=1)
            self.assertIsNotNone(locations)
            
            # Test journey search if location found
            if locations and len(locations) > 0:
                journeys = client.get_journeys(
                    locations[0].id, 
                    "8000261",  # München Hbf
                    results=1
                )
                # Don't assert success - API might be down, just test it doesn't crash
                print(f"Journey search result: {journeys is not None}")
        else:
            print("Live API not available - skipping live tests")


def run_test_matrix():
    """Run the complete test matrix"""
    print("🧪 Running Better-Bahn Real-time API Test Matrix")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAPIResponses,
        TestCachingLayer,
        TestMetricsCollection,
        TestGracefulDegradation,
        TestConfigurationManagement,
        TestIntegrationWithLiveAPI
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_test_matrix()
    sys.exit(0 if success else 1)