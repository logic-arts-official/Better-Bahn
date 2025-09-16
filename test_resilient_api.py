#!/usr/bin/env python3
"""
Comprehensive test suite for the resilient real-time API strategy.

This test suite validates the enhanced v6.db.transport.rest API implementation
including Result types, rate limiting, caching, and fallback strategies.
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch

from db_transport_api import (
    DBTransportAPIClient, 
    APIResult, 
    APIResultType, 
    TokenBucket, 
    CacheManager,
    CacheEntry
)


class TestAPIResultType(unittest.TestCase):
    """Test APIResult wrapper functionality."""
    
    def test_success_result(self):
        """Test successful API result."""
        result = APIResult(
            result_type=APIResultType.SUCCESS,
            data={"test": "data"},
            http_status=200
        )
        
        self.assertTrue(result.is_success)
        self.assertFalse(result.should_retry)
        self.assertFalse(result.can_fallback_to_cache)
        self.assertEqual(result.data, {"test": "data"})
    
    def test_rate_limited_result(self):
        """Test rate limited result properties."""
        result = APIResult(
            result_type=APIResultType.RATE_LIMITED,
            error_message="Rate limit exceeded",
            retry_after=60
        )
        
        self.assertFalse(result.is_success)
        self.assertTrue(result.should_retry)
        self.assertTrue(result.can_fallback_to_cache)
        self.assertEqual(result.retry_after, 60)
    
    def test_permanent_error_result(self):
        """Test permanent error result properties."""
        result = APIResult(
            result_type=APIResultType.PERMANENT_ERROR,
            error_message="Bad request",
            http_status=400
        )
        
        self.assertFalse(result.is_success)
        self.assertFalse(result.should_retry)
        self.assertFalse(result.can_fallback_to_cache)


class TestTokenBucket(unittest.TestCase):
    """Test token bucket rate limiting."""
    
    def test_initial_capacity(self):
        """Test initial token bucket state."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        self.assertEqual(bucket.tokens, 5)
        self.assertEqual(bucket.capacity, 5)
    
    def test_consume_tokens(self):
        """Test token consumption."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Should be able to consume available tokens
        self.assertTrue(bucket.consume(3))
        self.assertAlmostEqual(bucket.tokens, 2, places=3)
        
        # Should be able to consume remaining tokens
        self.assertTrue(bucket.consume(2))
        self.assertLess(bucket.tokens, 0.001)  # Essentially zero, accounting for floating point precision
        
        # Should not be able to consume when empty
        self.assertFalse(bucket.consume(1))
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=5, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        bucket.consume(5)
        self.assertEqual(bucket.tokens, 0)
        
        # Wait and check refill (simulate time passage)
        bucket.last_update = time.time() - 1.0  # Simulate 1 second ago
        
        # After 1 second at 2 tokens/sec, should have 2 tokens
        self.assertTrue(bucket.consume(1))  # This triggers refill calculation
        # Should have approximately 1 token left (2 refilled - 1 consumed)
        self.assertGreaterEqual(bucket.tokens, 0.9)
        self.assertLessEqual(bucket.tokens, 1.1)
    
    def test_time_until_available(self):
        """Test calculation of wait time for tokens."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)  # 1 token per second
        
        # Empty the bucket
        bucket.consume(5)
        
        # Should need 3 seconds for 3 tokens
        wait_time = bucket.time_until_available(3)
        self.assertEqual(wait_time, 3.0)
    
    def test_thread_safety(self):
        """Test token bucket thread safety."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        consumed_count = [0]
        
        def consumer():
            for _ in range(50):
                if bucket.consume(1):
                    consumed_count[0] += 1
        
        # Run multiple threads
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=consumer)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not exceed initial capacity
        self.assertLessEqual(consumed_count[0], 100)


class TestCacheManager(unittest.TestCase):
    """Test cache manager functionality."""
    
    def test_cache_entry_freshness(self):
        """Test cache entry freshness calculation."""
        entry = CacheEntry(
            data={"test": "data"},
            fetched_at=time.time() - 100,  # 100 seconds ago
            max_age=60  # 60 seconds max age
        )
        
        self.assertFalse(entry.is_fresh)
        self.assertTrue(entry.is_stale_but_usable)  # Within stale-while-revalidate window
    
    def test_cache_storage_and_retrieval(self):
        """Test basic cache operations."""
        cache = CacheManager(max_size=3)
        
        # Store entry
        entry = CacheEntry(data={"test": "data"}, fetched_at=time.time())
        cached_entry, key = cache.get("/test", {"param": "value"})
        self.assertIsNone(cached_entry)
        
        cache.set(key, entry)
        
        # Retrieve entry
        cached_entry, key2 = cache.get("/test", {"param": "value"})
        self.assertIsNotNone(cached_entry)
        self.assertEqual(key, key2)
        self.assertEqual(cached_entry.data, {"test": "data"})
    
    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        cache = CacheManager(max_size=2)
        
        # Fill cache to capacity
        entry1 = CacheEntry(data={"test": 1}, fetched_at=time.time())
        _, key1 = cache.get("/test1")
        cache.set(key1, entry1)
        
        entry2 = CacheEntry(data={"test": 2}, fetched_at=time.time())
        _, key2 = cache.get("/test2")
        cache.set(key2, entry2)
        
        # Add third entry (should evict oldest)
        entry3 = CacheEntry(data={"test": 3}, fetched_at=time.time())
        _, key3 = cache.get("/test3")
        cache.set(key3, entry3)
        
        # First entry should be evicted
        cached_entry1, _ = cache.get("/test1")
        self.assertIsNone(cached_entry1)
        
        # Other entries should still exist
        cached_entry2, _ = cache.get("/test2")
        cached_entry3, _ = cache.get("/test3")
        self.assertIsNotNone(cached_entry2)
        self.assertIsNotNone(cached_entry3)
    
    def test_cache_key_generation(self):
        """Test consistent cache key generation."""
        cache = CacheManager()
        
        # Same endpoint and params should generate same key
        _, key1 = cache.get("/test", {"a": 1, "b": 2})
        _, key2 = cache.get("/test", {"b": 2, "a": 1})  # Different order
        self.assertEqual(key1, key2)
        
        # Different params should generate different keys
        _, key3 = cache.get("/test", {"a": 1, "b": 3})
        self.assertNotEqual(key1, key3)


class TestDBTransportAPIClient(unittest.TestCase):
    """Test the enhanced DB Transport API client."""
    
    def setUp(self):
        """Set up test client."""
        self.client = DBTransportAPIClient(
            rate_limit_capacity=5,
            rate_limit_window=5.0,
            cache_max_size=10,
            enable_caching=True
        )
    
    def test_http_status_mapping(self):
        """Test HTTP status code to result type mapping."""
        # Test success codes
        self.assertEqual(
            self.client._map_http_status_to_result_type(200),
            APIResultType.SUCCESS
        )
        self.assertEqual(
            self.client._map_http_status_to_result_type(201),
            APIResultType.SUCCESS
        )
        
        # Test error codes
        self.assertEqual(
            self.client._map_http_status_to_result_type(404),
            APIResultType.NOT_FOUND
        )
        self.assertEqual(
            self.client._map_http_status_to_result_type(429),
            APIResultType.RATE_LIMITED
        )
        self.assertEqual(
            self.client._map_http_status_to_result_type(400),
            APIResultType.PERMANENT_ERROR
        )
        self.assertEqual(
            self.client._map_http_status_to_result_type(500),
            APIResultType.UPSTREAM_ERROR
        )
    
    @patch('requests.Session.get')
    def test_successful_request_with_caching(self, mock_get):
        """Test successful request and caching behavior."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.headers = {"ETag": "test-etag"}
        mock_get.return_value = mock_response
        
        # First request
        result1 = self.client._make_request_with_cache("/test")
        
        self.assertTrue(result1.is_success)
        self.assertEqual(result1.data, {"test": "data"})
        self.assertFalse(result1.from_cache)
        
        # Second request should use cache
        result2 = self.client._make_request_with_cache("/test")
        
        self.assertTrue(result2.is_success)
        self.assertEqual(result2.data, {"test": "data"})
        self.assertTrue(result2.from_cache)
        
        # Should only have made one actual HTTP request
        self.assertEqual(mock_get.call_count, 1)
    
    @patch('requests.Session.get')
    def test_rate_limiting_with_cache_fallback(self, mock_get):
        """Test rate limiting with cache fallback."""
        # Fill rate limiter
        for _ in range(5):
            self.client.rate_limiter.consume(1)
        
        # Mock cached data
        cache_entry = CacheEntry(
            data={"cached": "data"},
            fetched_at=time.time() - 400,  # Old but within stale-while-revalidate
            max_age=300
        )
        cache_key = "test-key"
        self.client.cache_manager.set(cache_key, cache_entry)
        
        # Mock the cache lookup to return our test data
        with patch.object(self.client.cache_manager, 'get', return_value=(cache_entry, cache_key)):
            result = self.client._make_request_with_cache("/test")
        
        # Should return cached data when rate limited
        self.assertTrue(result.is_success)
        self.assertTrue(result.from_cache)
        self.assertEqual(result.data, {"cached": "data"})
        
        # Should not have made HTTP request
        mock_get.assert_not_called()
    
    @patch('requests.Session.get')
    def test_error_handling_with_fallback(self, mock_get):
        """Test error handling with cache fallback."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        # Add cached data
        cache_entry = CacheEntry(
            data={"fallback": "data"},
            fetched_at=time.time() - 400,  # Stale but usable
            max_age=300
        )
        cache_key = "test-key"
        
        with patch.object(self.client.cache_manager, 'get', return_value=(cache_entry, cache_key)):
            result = self.client._make_request_with_cache("/test")
        
        # Should fallback to cached data on server error
        self.assertTrue(result.is_success)
        self.assertTrue(result.from_cache)
        self.assertEqual(result.data, {"fallback": "data"})
    
    @patch('requests.Session.get')
    def test_conditional_get_304_response(self, mock_get):
        """Test conditional GET with 304 Not Modified response."""
        # Mock 304 response
        mock_response = Mock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response
        
        # Add cached data with ETag
        cache_entry = CacheEntry(
            data={"cached": "data"},
            fetched_at=time.time() - 100,
            etag="test-etag",
            max_age=60
        )
        cache_key = "test-key"
        
        with patch.object(self.client.cache_manager, 'get', return_value=(cache_entry, cache_key)):
            with patch.object(self.client.cache_manager, 'set') as mock_set:
                result = self.client._make_request_with_cache("/test")
        
        # Should return cached data and update cache timestamp
        self.assertTrue(result.is_success)
        self.assertTrue(result.from_cache)
        self.assertEqual(result.data, {"cached": "data"})
        
        # Should have updated cache with fresh timestamp
        mock_set.assert_called_once()
    
    def test_backward_compatibility(self):
        """Test that legacy methods still work."""
        with patch.object(self.client, '_make_request_with_cache') as mock_resilient:
            mock_resilient.return_value = APIResult(
                result_type=APIResultType.SUCCESS,
                data=[{"id": "test", "name": "Test Station"}]
            )
            
            # Test legacy method
            result = self.client.find_locations("test", results=1)
            
            self.assertIsNotNone(result)
            self.assertEqual(result, [{"id": "test", "name": "Test Station"}])
            mock_resilient.assert_called_once()
    
    def test_statistics_tracking(self):
        """Test request statistics tracking."""
        initial_stats = self.client.get_stats()
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"test": "data"}
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            # Make request
            self.client._make_request_with_cache("/test")
            
            # Check statistics
            stats = self.client.get_stats()
            self.assertEqual(stats['requests_made'], initial_stats['requests_made'] + 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def test_main_integration_with_resilient_api(self):
        """Test main.py integration with enhanced API."""
        # Import here to avoid circular imports
        from main import get_real_time_journey_info
        
        # Test with mock data
        with patch('main.DBTransportAPIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock successful location search
            mock_client.find_locations_resilient.return_value = APIResult(
                result_type=APIResultType.SUCCESS,
                data=[{"id": "8011160", "name": "Berlin Hbf"}]
            )
            
            # Mock successful journey search
            mock_client.get_journeys_resilient.return_value = APIResult(
                result_type=APIResultType.SUCCESS,
                data={
                    "journeys": [{
                        "duration": 14400000,  # 4 hours in milliseconds
                        "legs": [{"id": "leg1"}, {"id": "leg2"}]
                    }]
                }
            )
            
            # Mock real-time status
            mock_client.get_real_time_status.return_value = {
                "has_delays": False,
                "total_delay_minutes": 0,
                "cancelled_legs": 0
            }
            
            # Mock statistics
            mock_client.get_stats.return_value = {
                "requests_made": 3,
                "cache_hits": 0,
                "rate_limit_hits": 0
            }
            
            # Test the function
            result = get_real_time_journey_info("Berlin", "München")
            
            # Verify result
            self.assertIsNotNone(result)
            self.assertTrue(result['available'])
            self.assertEqual(result['journeys_count'], 1)
            self.assertEqual(len(result['journeys']), 1)
            
            # Verify API calls were made
            mock_client.find_locations_resilient.assert_called()
            mock_client.get_journeys_resilient.assert_called()


def run_tests():
    """Run all tests and display results."""
    print("Running Resilient Real-time API Strategy Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAPIResultType,
        TestTokenBucket,
        TestCacheManager,
        TestDBTransportAPIClient,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall Result: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


if __name__ == "__main__":
    run_tests()