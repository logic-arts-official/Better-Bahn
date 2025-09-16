#!/usr/bin/env python3
"""
Performance benchmark tests for Better-Bahn functionality.

Tests YAML parsing performance, cache hit ratios, and rate limiting behavior.
"""

import unittest
import time
import yaml
import tempfile
import os
from unittest.mock import patch, mock_open, Mock
from collections import defaultdict

# Import functions under test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import load_timetable_masterdata
from db_transport_api import DBTransportAPIClient


class TestYAMLParsingPerformance(unittest.TestCase):
    """Benchmark YAML parsing performance."""

    def setUp(self):
        """Set up test fixtures for performance testing."""
        self.benchmark_results = {}

    def tearDown(self):
        """Print benchmark results."""
        if self.benchmark_results:
            print(f"\n{self._testMethodName} Results:")
            for test, duration in self.benchmark_results.items():
                print(f"  {test}: {duration:.4f}s")

    def _time_yaml_parsing(self, yaml_content, description):
        """Time YAML parsing and store results."""
        start_time = time.time()
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
                
        end_time = time.time()
        duration = end_time - start_time
        
        self.benchmark_results[description] = duration
        return result, duration

    def test_yaml_parsing_time_benchmarks(self):
        """Benchmark YAML parsing time for different file sizes."""
        
        # Small YAML (similar to minimal timetable schema)
        small_yaml = {
            'info': {'version': '1.0.213'},
            'components': {
                'schemas': {
                    'station': {'type': 'object'},
                    'connection': {'type': 'object'}
                }
            }
        }
        
        result, duration = self._time_yaml_parsing(
            yaml.dump(small_yaml), 
            "Small YAML (2 schemas)"
        )
        self.assertIsNotNone(result)
        self.assertLess(duration, 0.1)  # Should be very fast
        
        # Medium YAML (realistic timetable schema)
        medium_yaml = {
            'info': {'version': '1.0.213'},
            'components': {
                'schemas': {
                    f'schema_{i}': {
                        'type': 'object',
                        'properties': {
                            f'property_{j}': {
                                'type': 'string',
                                'description': f'Test property {j}'
                            }
                            for j in range(10)
                        }
                    }
                    for i in range(20)
                }
            }
        }
        
        result, duration = self._time_yaml_parsing(
            yaml.dump(medium_yaml), 
            "Medium YAML (20 schemas, 200 properties)"
        )
        self.assertIsNotNone(result)
        self.assertLess(duration, 0.5)  # Should still be fast
        
        # Large YAML (stress test)
        large_yaml = {
            'info': {'version': '1.0.213'},
            'components': {
                'schemas': {
                    f'schema_{i}': {
                        'type': 'object',
                        'required': [f'prop_{j}' for j in range(5)],
                        'properties': {
                            f'property_{j}': {
                                'type': 'string',
                                'description': f'Test property {j} for schema {i}',
                                'enum': [f'value_{k}' for k in range(3)]
                            }
                            for j in range(20)
                        }
                    }
                    for i in range(100)
                }
            },
            'paths': {
                f'/endpoint_{i}': {
                    'get': {
                        'responses': {
                            '200': {'description': 'Success'}
                        }
                    }
                }
                for i in range(50)
            }
        }
        
        result, duration = self._time_yaml_parsing(
            yaml.dump(large_yaml), 
            "Large YAML (100 schemas, 2000 properties, 50 paths)"
        )
        self.assertIsNotNone(result)
        self.assertLess(duration, 2.0)  # Should complete within reasonable time

    def test_yaml_parsing_memory_efficiency(self):
        """Test that YAML parsing doesn't consume excessive memory."""
        # This is a basic test - in a real scenario you'd use memory profiling tools
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Parse a reasonably large YAML
        large_yaml = {
            'data': {
                f'item_{i}': {
                    'name': f'Item {i}',
                    'description': f'Description for item {i}' * 10,
                    'metadata': {
                        f'key_{j}': f'value_{j}' for j in range(20)
                    }
                }
                for i in range(1000)
            }
        }
        
        yaml_content = yaml.dump(large_yaml)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.join', return_value='mocked_path'):
                result = load_timetable_masterdata()
        
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        memory_increase_mb = memory_increase / (1024 * 1024)
        self.assertLess(memory_increase_mb, 100)
        
        self.benchmark_results['Memory increase (MB)'] = memory_increase_mb

    def test_yaml_parsing_malformed_performance(self):
        """Test performance when parsing malformed YAML."""
        malformed_yamls = [
            "invalid: yaml: content: [",  # Unclosed bracket
            "{'json': 'instead of yaml'}",  # JSON-like
            "key: value\n\tindented with tab",  # Tab indentation
            "key: value\n" + "x" * 10000,  # Very long line
            "---\nduplicate: key\nduplicate: key",  # Duplicate keys
        ]
        
        for i, yaml_content in enumerate(malformed_yamls):
            start_time = time.time()
            
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.join', return_value='mocked_path'):
                    result = load_timetable_masterdata()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should handle malformed YAML quickly and gracefully
            self.assertLess(duration, 1.0)
            # Should return None for malformed YAML
            if i in [0, 2]:  # These should definitely fail
                self.assertIsNone(result)
            
            self.benchmark_results[f'Malformed YAML {i+1}'] = duration


class TestCachePerformance(unittest.TestCase):
    """Test cache hit ratios and performance under typical usage patterns."""

    def setUp(self):
        """Set up cache performance testing."""
        self.api_client = DBTransportAPIClient(rate_limit_delay=0.01)
        self.request_log = []
        self.cache_hits = 0
        self.cache_misses = 0

    def _mock_cached_api_call(self, endpoint, params=None):
        """Mock API call with simple caching simulation."""
        cache_key = f"{endpoint}:{str(sorted(params.items()) if params else '')}"
        
        # Simulate cache lookup
        if cache_key in self._cache:
            self.cache_hits += 1
            return self._cache[cache_key]
        else:
            self.cache_misses += 1
            # Simulate API response
            response = {'cached': False, 'endpoint': endpoint, 'params': params}
            self._cache[cache_key] = response
            return response

    def test_cache_hit_ratio_typical_ui_polling(self):
        """Test cache hit ratio under typical UI polling patterns."""
        self._cache = {}
        
        # Simulate typical UI polling pattern:
        # User checks same route multiple times with slight variations
        routes = [
            ('Berlin Hbf', 'München Hbf'),
            ('Berlin Hbf', 'Hamburg Hbf'),
            ('München Hbf', 'Frankfurt Hbf'),
        ]
        
        # Simulate 20 requests with some repetition (typical user behavior)
        requests = []
        for _ in range(20):
            route = routes[len(requests) % len(routes)]
            # Slight time variations (user refreshing)
            time_offset = (len(requests) % 4) * 5  # 0, 5, 10, 15 minute offsets
            requests.append((route[0], route[1], f"10:{time_offset:02d}"))
        
        # Execute requests with cache simulation
        for from_station, to_station, time_str in requests:
            self._mock_cached_api_call(
                '/journeys',
                {'from': from_station, 'to': to_station, 'time': time_str}
            )
        
        # Calculate cache hit ratio
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total_requests if total_requests > 0 else 0
        
        print(f"\nCache Performance Results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Cache hits: {self.cache_hits}")
        print(f"  Cache misses: {self.cache_misses}")
        print(f"  Hit ratio: {hit_ratio:.2%}")
        
        # Should achieve at least 70% hit ratio as specified in requirements
        self.assertGreaterEqual(hit_ratio, 0.70)

    def test_cache_performance_with_time_variations(self):
        """Test cache performance when users request similar times."""
        self._cache = {}
        
        # Simulate user checking same route at different times
        base_route = ('Berlin Hbf', 'München Hbf')
        times = ['09:00', '09:15', '09:30', '10:00', '10:15', '10:30']
        
        # First pass - populate cache
        for time_str in times:
            self._mock_cached_api_call(
                '/journeys',
                {'from': base_route[0], 'to': base_route[1], 'departure': time_str}
            )
        
        # Second pass - should hit cache for repeated requests
        for time_str in times[:3]:  # Repeat first 3 times
            self._mock_cached_api_call(
                '/journeys',
                {'from': base_route[0], 'to': base_route[1], 'departure': time_str}
            )
        
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total_requests
        
        print(f"\nTime Variation Cache Results:")
        print(f"  Hit ratio: {hit_ratio:.2%}")
        
        # Should achieve good hit ratio for repeated time requests
        self.assertGreaterEqual(hit_ratio, 0.33)  # 3 out of 9 should be hits

    def test_cache_invalidation_behavior(self):
        """Test cache behavior with time-based invalidation simulation."""
        self._cache = {}
        cache_timestamps = {}
        current_time = time.time()
        
        def cached_api_call_with_ttl(endpoint, params, ttl_seconds=300):
            """Simulate API call with TTL-based cache."""
            cache_key = f"{endpoint}:{str(sorted(params.items()) if params else '')}"
            
            # Check if cached and not expired
            if cache_key in self._cache:
                if current_time - cache_timestamps[cache_key] < ttl_seconds:
                    self.cache_hits += 1
                    return self._cache[cache_key]
                else:
                    # Cache expired
                    del self._cache[cache_key]
                    del cache_timestamps[cache_key]
            
            # Cache miss or expired
            self.cache_misses += 1
            response = {'endpoint': endpoint, 'timestamp': current_time}
            self._cache[cache_key] = response
            cache_timestamps[cache_key] = current_time
            return response
        
        # Test multiple requests for same data
        route_params = {'from': 'Berlin Hbf', 'to': 'München Hbf'}
        
        # Initial request
        cached_api_call_with_ttl('/journeys', route_params)
        
        # Immediate repeat - should hit cache
        cached_api_call_with_ttl('/journeys', route_params)
        
        # Simulate time passing but within TTL
        current_time += 60  # 1 minute later
        cached_api_call_with_ttl('/journeys', route_params)
        
        # Simulate time passing beyond TTL
        current_time += 300  # 5 minutes later (beyond 5-minute TTL)
        cached_api_call_with_ttl('/journeys', route_params)
        
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total_requests
        
        print(f"\nTTL Cache Results:")
        print(f"  Hit ratio: {hit_ratio:.2%}")
        
        # Should have 2 hits out of 4 requests (2nd and 3rd should hit cache)
        self.assertEqual(self.cache_hits, 2)
        self.assertEqual(self.cache_misses, 2)


class TestRateLimitingPerformance(unittest.TestCase):
    """Test rate limiting behavior and performance."""

    def test_rate_limiting_delay_accuracy(self):
        """Test that rate limiting delays are applied accurately."""
        client = DBTransportAPIClient(rate_limit_delay=0.1)
        
        request_times = []
        
        # Mock successful responses
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'test': 'data'}
            mock_get.return_value = mock_response
            
            # Make multiple requests and time them
            for i in range(5):
                start_time = time.time()
                client._make_request('/test')
                end_time = time.time()
                request_times.append(end_time - start_time)
        
        # Each request should take at least the rate limit delay
        for request_time in request_times:
            self.assertGreaterEqual(request_time, 0.1)
        
        # Average request time should be close to rate limit + small processing overhead
        avg_time = sum(request_times) / len(request_times)
        self.assertLess(avg_time, 0.2)  # Should not be much slower than rate limit

    def test_rapid_refresh_rate_limiting(self):
        """Test rapid refresh scenario - 5 clicks in 5 seconds."""
        client = DBTransportAPIClient(rate_limit_delay=0.2)
        
        start_time = time.time()
        request_count = 0
        
        # Mock responses
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'test': 'data'}
            mock_get.return_value = mock_response
            
            # Simulate rapid clicking - 5 requests as fast as possible
            for i in range(5):
                client._make_request('/test')
                request_count += 1
        
        total_time = time.time() - start_time
        
        print(f"\nRapid Refresh Results:")
        print(f"  5 requests completed in: {total_time:.2f}s")
        print(f"  Average time per request: {total_time/5:.2f}s")
        
        # With 0.2s rate limiting, 5 requests should take at least 1 second
        self.assertGreaterEqual(total_time, 1.0)
        
        # Should not take excessively long (under 2 seconds for 5 requests)
        self.assertLess(total_time, 2.0)

    def test_concurrent_request_handling(self):
        """Test behavior under simulated concurrent load."""
        import threading
        import queue
        
        client = DBTransportAPIClient(rate_limit_delay=0.05)
        results_queue = queue.Queue()
        
        def make_request(request_id):
            """Make a single API request and record timing."""
            start_time = time.time()
            
            with patch.object(client.session, 'get') as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {'request_id': request_id}
                mock_get.return_value = mock_response
                
                result = client._make_request(f'/test/{request_id}')
                
            end_time = time.time()
            results_queue.put({
                'request_id': request_id,
                'duration': end_time - start_time,
                'success': result is not None
            })
        
        # Start multiple threads to simulate concurrent requests
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        success_count = sum(1 for r in results if r['success'])
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        print(f"\nConcurrent Request Results:")
        print(f"  Total requests: {len(results)}")
        print(f"  Successful requests: {success_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average request duration: {avg_duration:.2f}s")
        
        # All requests should succeed
        self.assertEqual(success_count, 10)
        
        # Average duration should respect rate limiting
        self.assertGreaterEqual(avg_duration, 0.05)


if __name__ == '__main__':
    # Run benchmarks
    unittest.main(verbosity=2)