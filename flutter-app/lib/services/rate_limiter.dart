/// Rate limiting service for API requests to prevent HTTP 429 errors
/// 
/// This service implements proper rate limiting for bahn.de API requests
/// with exponential backoff and request caching to prevent duplicate requests.

import 'dart:async';
import 'dart:math';

/// Rate limiter with exponential backoff support
class RateLimiter {
  static const Duration _defaultDelay = Duration(milliseconds: 1000);
  static const Duration _maxDelay = Duration(seconds: 30);
  static const int _maxRetries = 5;
  
  final Duration baseDelay;
  final Duration maxDelay;
  final int maxRetries;
  
  DateTime _lastRequestTime = DateTime.fromMillisecondsSinceEpoch(0);
  final Map<String, DateTime> _requestTimes = {};
  final Map<String, dynamic> _requestCache = {};
  
  RateLimiter({
    this.baseDelay = _defaultDelay,
    this.maxDelay = _maxDelay,
    this.maxRetries = _maxRetries,
  });
  
  /// Wait for rate limiting before making a request
  Future<void> waitForRateLimit([String? requestKey]) async {
    final now = DateTime.now();
    final timeSinceLastRequest = now.difference(_lastRequestTime);
    
    if (timeSinceLastRequest < baseDelay) {
      final waitTime = baseDelay - timeSinceLastRequest;
      await Future.delayed(waitTime);
    }
    
    _lastRequestTime = DateTime.now();
    
    if (requestKey != null) {
      _requestTimes[requestKey] = _lastRequestTime;
    }
  }
  
  /// Calculate exponential backoff delay for retry attempts
  Duration calculateBackoffDelay(int attempt) {
    final delayMs = baseDelay.inMilliseconds * pow(2, attempt).toInt();
    final maxDelayMs = maxDelay.inMilliseconds;
    final actualDelayMs = min(delayMs, maxDelayMs);
    
    // Add some jitter to prevent thundering herd
    final jitter = Random().nextInt(actualDelayMs ~/ 4);
    return Duration(milliseconds: actualDelayMs + jitter);
  }
  
  /// Check if a request was made recently
  bool isRecentRequest(String requestKey, Duration threshold) {
    final lastRequest = _requestTimes[requestKey];
    if (lastRequest == null) return false;
    
    return DateTime.now().difference(lastRequest) < threshold;
  }
  
  /// Cache a request result
  void cacheResult(String key, dynamic result, {Duration? ttl}) {
    _requestCache[key] = {
      'result': result,
      'timestamp': DateTime.now(),
      'ttl': ttl ?? const Duration(minutes: 5),
    };
  }
  
  /// Get cached result if available and not expired
  dynamic getCachedResult(String key) {
    final cached = _requestCache[key];
    if (cached == null) return null;
    
    final age = DateTime.now().difference(cached['timestamp'] as DateTime);
    final ttl = cached['ttl'] as Duration;
    
    if (age > ttl) {
      _requestCache.remove(key);
      return null;
    }
    
    return cached['result'];
  }
  
  /// Clear expired cache entries
  void clearExpiredCache() {
    final now = DateTime.now();
    _requestCache.removeWhere((key, cached) {
      final age = now.difference(cached['timestamp'] as DateTime);
      final ttl = cached['ttl'] as Duration;
      return age > ttl;
    });
  }
  
  /// Execute a request with rate limiting and exponential backoff
  Future<T> executeWithRetry<T>(
    Future<T> Function() request, {
    String? cacheKey,
    Duration? cacheTtl,
    bool Function(Exception)? shouldRetry,
  }) async {
    // Check cache first
    if (cacheKey != null) {
      final cached = getCachedResult(cacheKey);
      if (cached != null) {
        return cached as T;
      }
    }
    
    Exception? lastException;
    
    for (int attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Rate limiting
        await waitForRateLimit(cacheKey);
        
        // Execute request
        final result = await request();
        
        // Cache successful result
        if (cacheKey != null) {
          cacheResult(cacheKey, result, ttl: cacheTtl);
        }
        
        return result;
        
      } catch (e) {
        lastException = e is Exception ? e : Exception(e.toString());
        
        // Don't retry if this is the last attempt
        if (attempt == maxRetries - 1) break;
        
        // Check if we should retry this exception
        if (shouldRetry != null && !shouldRetry(lastException)) break;
        
        // Check if this is a rate limiting error (HTTP 429)
        final isRateLimited = e.toString().contains('429') || 
                            e.toString().toLowerCase().contains('too many requests');
        
        if (isRateLimited) {
          // Use exponential backoff for rate limiting errors
          final backoffDelay = calculateBackoffDelay(attempt);
          await Future.delayed(backoffDelay);
        } else {
          // Regular retry delay
          await Future.delayed(Duration(milliseconds: 500 * (attempt + 1)));
        }
      }
    }
    
    throw lastException ?? Exception('Request failed after $maxRetries attempts');
  }
}

/// Singleton instance for global rate limiting
final globalRateLimiter = RateLimiter();