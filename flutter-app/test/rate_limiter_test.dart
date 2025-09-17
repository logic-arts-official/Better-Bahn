/// Test file for rate limiter functionality
/// This can be run to verify the rate limiting works correctly

import 'package:flutter_test/flutter_test.dart';
import '../lib/services/rate_limiter.dart';

void main() {
  group('RateLimiter Tests', () {
    test('should delay between requests', () async {
      final rateLimiter = RateLimiter(
        baseDelay: Duration(milliseconds: 100),
      );
      
      final stopwatch = Stopwatch()..start();
      
      // Make two quick requests
      await rateLimiter.waitForRateLimit('test1');
      final firstRequestTime = stopwatch.elapsedMilliseconds;
      
      await rateLimiter.waitForRateLimit('test2');
      final secondRequestTime = stopwatch.elapsedMilliseconds;
      
      // Second request should be delayed by at least the base delay
      expect(secondRequestTime - firstRequestTime, greaterThanOrEqualTo(90));
    });
    
    test('should cache results', () async {
      final rateLimiter = RateLimiter();
      
      // Cache a result
      rateLimiter.cacheResult('test_key', {'data': 'test'});
      
      // Should return cached result
      final result = rateLimiter.getCachedResult('test_key');
      expect(result, equals({'data': 'test'}));
    });
    
    test('should clear expired cache', () async {
      final rateLimiter = RateLimiter();
      
      // Cache with very short TTL
      rateLimiter.cacheResult('test_key', {'data': 'test'}, 
          ttl: Duration(milliseconds: 1));
      
      // Wait for expiration
      await Future.delayed(Duration(milliseconds: 10));
      
      // Clear expired cache
      rateLimiter.clearExpiredCache();
      
      // Should return null for expired cache
      final result = rateLimiter.getCachedResult('test_key');
      expect(result, isNull);
    });
    
    test('should calculate exponential backoff', () {
      final rateLimiter = RateLimiter(baseDelay: Duration(milliseconds: 100));
      
      // Test backoff delays
      final delay0 = rateLimiter.calculateBackoffDelay(0);
      final delay1 = rateLimiter.calculateBackoffDelay(1);
      final delay2 = rateLimiter.calculateBackoffDelay(2);
      
      // Each delay should be roughly double the previous (with jitter)
      expect(delay0.inMilliseconds, greaterThanOrEqualTo(100));
      expect(delay1.inMilliseconds, greaterThanOrEqualTo(200));
      expect(delay2.inMilliseconds, greaterThanOrEqualTo(400));
    });
    
    test('should retry with exponential backoff on HTTP 429', () async {
      final rateLimiter = RateLimiter(
        baseDelay: Duration(milliseconds: 10),
        maxRetries: 3,
      );
      
      int attempts = 0;
      
      try {
        await rateLimiter.executeWithRetry<String>(
          () async {
            attempts++;
            if (attempts < 3) {
              throw Exception('429 Too Many Requests');
            }
            return 'success';
          },
          cacheKey: 'retry_test',
        );
      } catch (e) {
        // Test should succeed after retries
      }
      
      // Should have made 3 attempts
      expect(attempts, equals(3));
    });
  });
}