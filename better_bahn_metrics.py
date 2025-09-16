"""
Metrics collection and logging system for Better-Bahn API integration.
Tracks latency, HTTP status codes, cache performance, and other key metrics.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock
import statistics

from better_bahn_config import LoggingConfig


@dataclass
class LatencyBucket:
    """Represents a latency measurement bucket"""
    min_ms: float
    max_ms: float
    count: int = 0
    
    def __post_init__(self):
        self.label = f"{self.min_ms:.0f}ms-{self.max_ms:.0f}ms"
    
    def includes(self, latency_ms: float) -> bool:
        """Check if latency falls in this bucket"""
        return self.min_ms <= latency_ms < self.max_ms


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    timestamp: float
    url: str
    method: str
    status_code: Optional[int]
    latency_ms: float
    cache_hit: bool
    cache_source: Optional[str]
    error: Optional[str] = None


class MetricsCollector:
    """Collects and aggregates metrics for Better-Bahn API calls"""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.logger = logging.getLogger('better_bahn.metrics')
        self._lock = Lock()
        
        # Request history (keeping last 1000 requests)
        self._request_history: deque = deque(maxlen=1000)
        
        # Latency buckets (in milliseconds)
        self._latency_buckets = [
            LatencyBucket(0, 100),      # Very fast
            LatencyBucket(100, 500),    # Fast
            LatencyBucket(500, 1000),   # Medium
            LatencyBucket(1000, 2000),  # Slow
            LatencyBucket(2000, 5000),  # Very slow
            LatencyBucket(5000, float('inf'))  # Timeout range
        ]
        
        # Status code counters
        self._status_codes: Dict[int, int] = defaultdict(int)
        
        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_sources: Dict[str, int] = defaultdict(int)
        
        # Error tracking
        self._errors: Dict[str, int] = defaultdict(int)
        
        # Timing
        self._start_time = time.time()
    
    def record_request(self, 
                      url: str,
                      method: str = "GET",
                      status_code: Optional[int] = None,
                      latency_ms: float = 0.0,
                      cache_hit: bool = False,
                      cache_source: Optional[str] = None,
                      error: Optional[str] = None) -> None:
        """Record metrics for an API request"""
        
        if not self.config.enable_metrics:
            return
        
        with self._lock:
            # Create request metrics
            metrics = RequestMetrics(
                timestamp=time.time(),
                url=url,
                method=method,
                status_code=status_code,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                cache_source=cache_source,
                error=error
            )
            
            # Store in history
            self._request_history.append(metrics)
            
            # Update latency buckets
            if self.config.track_latency and latency_ms > 0:
                for bucket in self._latency_buckets:
                    if bucket.includes(latency_ms):
                        bucket.count += 1
                        break
            
            # Update status code distribution
            if self.config.track_status_codes and status_code:
                self._status_codes[status_code] += 1
            
            # Update cache metrics
            if self.config.track_cache_hits:
                if cache_hit:
                    self._cache_hits += 1
                    if cache_source:
                        self._cache_sources[cache_source] += 1
                else:
                    self._cache_misses += 1
            
            # Update error tracking
            if error:
                self._errors[error] += 1
            
            # Log significant events
            if error:
                self.logger.warning(f"API error: {error} for {method} {url}")
            elif status_code and status_code >= 400:
                self.logger.warning(f"HTTP {status_code} for {method} {url} (latency: {latency_ms:.1f}ms)")
            elif latency_ms > 5000:
                self.logger.warning(f"Slow request: {latency_ms:.1f}ms for {method} {url}")
            else:
                self.logger.debug(f"{method} {url} - {status_code} ({latency_ms:.1f}ms, cache: {cache_hit})")
    
    def get_latency_stats(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get latency statistics for recent requests"""
        
        if not self.config.track_latency:
            return {}
        
        with self._lock:
            cutoff_time = time.time() - (window_minutes * 60)
            recent_requests = [
                req for req in self._request_history 
                if req.timestamp > cutoff_time and req.latency_ms > 0
            ]
            
            if not recent_requests:
                return {
                    'count': 0,
                    'window_minutes': window_minutes
                }
            
            latencies = [req.latency_ms for req in recent_requests]
            
            return {
                'count': len(latencies),
                'window_minutes': window_minutes,
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'mean_ms': statistics.mean(latencies),
                'median_ms': statistics.median(latencies),
                'p95_ms': self._percentile(latencies, 0.95),
                'p99_ms': self._percentile(latencies, 0.99),
                'buckets': {
                    bucket.label: bucket.count 
                    for bucket in self._latency_buckets 
                    if bucket.count > 0
                }
            }
    
    def get_status_distribution(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get HTTP status code distribution"""
        
        if not self.config.track_status_codes:
            return {}
        
        with self._lock:
            cutoff_time = time.time() - (window_minutes * 60)
            recent_requests = [
                req for req in self._request_history 
                if req.timestamp > cutoff_time and req.status_code
            ]
            
            if not recent_requests:
                return {
                    'count': 0,
                    'window_minutes': window_minutes
                }
            
            # Count status codes in window
            status_counts = defaultdict(int)
            for req in recent_requests:
                status_counts[req.status_code] += 1
            
            total_requests = len(recent_requests)
            
            return {
                'count': total_requests,
                'window_minutes': window_minutes,
                'distribution': dict(status_counts),
                'success_rate': sum(
                    count for status, count in status_counts.items() 
                    if 200 <= status < 300
                ) / total_requests if total_requests > 0 else 0.0,
                'error_rate': sum(
                    count for status, count in status_counts.items() 
                    if status >= 400
                ) / total_requests if total_requests > 0 else 0.0
            }
    
    def get_cache_stats(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get cache performance statistics"""
        
        if not self.config.track_cache_hits:
            return {}
        
        with self._lock:
            cutoff_time = time.time() - (window_minutes * 60)
            recent_requests = [
                req for req in self._request_history 
                if req.timestamp > cutoff_time
            ]
            
            if not recent_requests:
                return {
                    'count': 0,
                    'window_minutes': window_minutes
                }
            
            cache_hits = sum(1 for req in recent_requests if req.cache_hit)
            total_requests = len(recent_requests)
            
            # Count cache sources
            source_counts = defaultdict(int)
            for req in recent_requests:
                if req.cache_hit and req.cache_source:
                    source_counts[req.cache_source] += 1
            
            return {
                'count': total_requests,
                'window_minutes': window_minutes,
                'hits': cache_hits,
                'misses': total_requests - cache_hits,
                'hit_rate': cache_hits / total_requests if total_requests > 0 else 0.0,
                'sources': dict(source_counts)
            }
    
    def get_error_stats(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get error statistics"""
        
        with self._lock:
            cutoff_time = time.time() - (window_minutes * 60)
            recent_requests = [
                req for req in self._request_history 
                if req.timestamp > cutoff_time
            ]
            
            if not recent_requests:
                return {
                    'count': 0,
                    'window_minutes': window_minutes
                }
            
            error_counts = defaultdict(int)
            total_errors = 0
            
            for req in recent_requests:
                if req.error:
                    error_counts[req.error] += 1
                    total_errors += 1
            
            total_requests = len(recent_requests)
            
            return {
                'count': total_requests,
                'window_minutes': window_minutes,
                'total_errors': total_errors,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0.0,
                'error_types': dict(error_counts)
            }
    
    def get_comprehensive_stats(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get all statistics in one call"""
        
        return {
            'latency': self.get_latency_stats(window_minutes),
            'status_codes': self.get_status_distribution(window_minutes),
            'cache': self.get_cache_stats(window_minutes),
            'errors': self.get_error_stats(window_minutes),
            'uptime_seconds': time.time() - self._start_time,
            'total_requests': len(self._request_history)
        }
    
    def log_summary(self, window_minutes: int = 10) -> None:
        """Log a summary of recent metrics"""
        
        stats = self.get_comprehensive_stats(window_minutes)
        
        if stats['latency']['count'] == 0:
            self.logger.info(f"No requests in last {window_minutes} minutes")
            return
        
        # Format latency summary
        latency = stats['latency']
        self.logger.info(
            f"Last {window_minutes}min: {latency['count']} requests, "
            f"latency p50={latency.get('median_ms', 0):.1f}ms "
            f"p95={latency.get('p95_ms', 0):.1f}ms"
        )
        
        # Format cache summary
        cache = stats['cache']
        if cache['count'] > 0:
            self.logger.info(
                f"Cache: {cache['hit_rate']:.1%} hit rate "
                f"({cache['hits']}/{cache['count']} requests)"
            )
        
        # Format error summary
        errors = stats['errors']
        if errors['total_errors'] > 0:
            self.logger.warning(
                f"Errors: {errors['error_rate']:.1%} error rate "
                f"({errors['total_errors']}/{errors['count']} requests)"
            )
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self._request_history.clear()
            
            for bucket in self._latency_buckets:
                bucket.count = 0
            
            self._status_codes.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._cache_sources.clear()
            self._errors.clear()
            self._start_time = time.time()
        
        self.logger.info("Metrics reset")
    
    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        """Calculate percentile of a list"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_data):
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        else:
            return sorted_data[f]


class PerformanceTimer:
    """Context manager for measuring execution time"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None,
                 url: str = "", method: str = "GET"):
        self.metrics_collector = metrics_collector
        self.url = url
        self.method = method
        self.start_time = None
        self.latency_ms = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.latency_ms = (time.time() - self.start_time) * 1000
            
            if self.metrics_collector:
                error = None
                if exc_type:
                    error = exc_type.__name__
                
                self.metrics_collector.record_request(
                    url=self.url,
                    method=self.method,
                    latency_ms=self.latency_ms,
                    error=error
                )