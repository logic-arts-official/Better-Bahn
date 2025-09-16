"""
Caching layer for Better-Bahn API responses.
Supports both memory and disk caching with TTL-based expiration.
"""

import time
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
import pickle
import os

from better_bahn_config import CacheConfig


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata"""
    data: Any
    timestamp: float
    ttl_seconds: int
    access_count: int = 0
    last_access: float = 0.0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.timestamp > self.ttl_seconds
    
    @property
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds"""
        return int(time.time() - self.timestamp)
    
    def access(self) -> Any:
        """Record access and return data"""
        self.access_count += 1
        self.last_access = time.time()
        return self.data


class MemoryCache:
    """Thread-safe in-memory cache with LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 30):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: Dict[str, float] = {}
        self._lock = Lock()
        self.logger = logging.getLogger('better_bahn.cache.memory')
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _make_key(self, key: Union[str, Dict]) -> str:
        """Create a consistent cache key"""
        if isinstance(key, dict):
            # Sort dictionary for consistent hashing
            sorted_items = sorted(key.items())
            key_str = json.dumps(sorted_items, sort_keys=True)
        else:
            key_str = str(key)
        
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _evict_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry.timestamp > entry.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._access_order.pop(key, None)
            self.evictions += 1
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries to make space"""
        while len(self._cache) >= self.max_size:
            if not self._access_order:
                break
            
            # Find oldest access time
            oldest_key = min(self._access_order.keys(), 
                           key=lambda k: self._access_order[k])
            
            del self._cache[oldest_key]
            del self._access_order[oldest_key]
            self.evictions += 1
    
    def get(self, key: Union[str, Dict]) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._make_key(key)
        
        with self._lock:
            entry = self._cache.get(cache_key)
            
            if entry is None:
                self.misses += 1
                self.logger.debug(f"Cache miss for key: {cache_key[:16]}...")
                return None
            
            if entry.is_expired:
                del self._cache[cache_key]
                self._access_order.pop(cache_key, None)
                self.misses += 1
                self.evictions += 1
                self.logger.debug(f"Cache expired for key: {cache_key[:16]}...")
                return None
            
            # Update access order
            self._access_order[cache_key] = time.time()
            self.hits += 1
            
            self.logger.debug(f"Cache hit for key: {cache_key[:16]}... (age: {entry.age_seconds}s)")
            return entry.access()
    
    def set(self, key: Union[str, Dict], value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Clean up expired entries
            self._evict_expired()
            
            # Make space if needed
            if cache_key not in self._cache:
                self._evict_lru()
            
            # Store entry
            self._cache[cache_key] = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl_seconds=ttl
            )
            self._access_order[cache_key] = time.time()
            
            self.logger.debug(f"Cached value for key: {cache_key[:16]}... (TTL: {ttl}s)")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self.logger.info("Memory cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self._cache),
                'max_size': self.max_size,
                'evictions': self.evictions
            }


class DiskCache:
    """Persistent disk cache for offline fallback"""
    
    def __init__(self, cache_dir: str = "/tmp/better_bahn_cache", default_ttl: int = 300):
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.logger = logging.getLogger('better_bahn.cache.disk')
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.hits = 0
        self.misses = 0
    
    def _make_filename(self, key: Union[str, Dict]) -> str:
        """Create filename for cache entry"""
        if isinstance(key, dict):
            sorted_items = sorted(key.items())
            key_str = json.dumps(sorted_items, sort_keys=True)
        else:
            key_str = str(key)
        
        hash_key = hashlib.sha256(key_str.encode()).hexdigest()
        return f"{hash_key}.cache"
    
    def _get_cache_path(self, key: Union[str, Dict]) -> Path:
        """Get full path for cache file"""
        filename = self._make_filename(key)
        return self.cache_dir / filename
    
    def get(self, key: Union[str, Dict]) -> Optional[Any]:
        """Get value from disk cache"""
        cache_path = self._get_cache_path(key)
        
        try:
            if not cache_path.exists():
                self.misses += 1
                return None
            
            # Load cache entry
            with open(cache_path, 'rb') as f:
                entry = pickle.load(f)
            
            if not isinstance(entry, CacheEntry):
                self.misses += 1
                return None
            
            if entry.is_expired:
                # Clean up expired file
                cache_path.unlink(missing_ok=True)
                self.misses += 1
                self.logger.debug(f"Disk cache expired: {cache_path.name}")
                return None
            
            self.hits += 1
            self.logger.debug(f"Disk cache hit: {cache_path.name} (age: {entry.age_seconds}s)")
            return entry.access()
            
        except (OSError, pickle.PickleError, EOFError) as e:
            self.logger.warning(f"Failed to read disk cache {cache_path.name}: {e}")
            self.misses += 1
            return None
    
    def set(self, key: Union[str, Dict], value: Any, ttl: Optional[int] = None) -> None:
        """Set value in disk cache"""
        cache_path = self._get_cache_path(key)
        ttl = ttl or self.default_ttl
        
        try:
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl_seconds=ttl
            )
            
            with open(cache_path, 'wb') as f:
                pickle.dump(entry, f)
            
            self.logger.debug(f"Disk cached: {cache_path.name} (TTL: {ttl}s)")
            
        except (OSError, pickle.PickleError) as e:
            self.logger.warning(f"Failed to write disk cache {cache_path.name}: {e}")
    
    def clear(self) -> None:
        """Clear all disk cache entries"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
            self.logger.info("Disk cache cleared")
        except OSError as e:
            self.logger.warning(f"Failed to clear disk cache: {e}")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache files and return count"""
        removed_count = 0
        
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    
                    if isinstance(entry, CacheEntry) and entry.is_expired:
                        cache_file.unlink(missing_ok=True)
                        removed_count += 1
                        
                except (OSError, pickle.PickleError, EOFError):
                    # Remove corrupted files
                    cache_file.unlink(missing_ok=True)
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} expired disk cache entries")
                
        except OSError as e:
            self.logger.warning(f"Failed to cleanup disk cache: {e}")
        
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        # Count cache files
        cache_files = 0
        cache_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_files += 1
                cache_size += cache_file.stat().st_size
        except OSError:
            pass
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'files': cache_files,
            'size_bytes': cache_size,
            'cache_dir': str(self.cache_dir)
        }


class CacheManager:
    """Manages both memory and disk caches"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.logger = logging.getLogger('better_bahn.cache')
        
        # Initialize caches based on configuration
        self.memory_cache = None
        self.disk_cache = None
        
        if config.enable_memory_cache:
            self.memory_cache = MemoryCache(
                max_size=config.memory_cache_max_size,
                default_ttl=config.memory_cache_ttl
            )
            self.logger.info(f"Memory cache enabled (TTL: {config.memory_cache_ttl}s, size: {config.memory_cache_max_size})")
        
        if config.enable_disk_cache:
            self.disk_cache = DiskCache(
                cache_dir=config.disk_cache_dir,
                default_ttl=config.disk_cache_ttl
            )
            self.logger.info(f"Disk cache enabled (TTL: {config.disk_cache_ttl}s, dir: {config.disk_cache_dir})")
    
    def get(self, key: Union[str, Dict], use_stale: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get value from cache with fallback chain.
        
        Args:
            key: Cache key
            use_stale: Whether to use expired data as stale fallback
            
        Returns:
            Dict with 'data' and 'metadata' or None
        """
        
        # Try memory cache first
        if self.memory_cache:
            result = self.memory_cache.get(key)
            if result is not None:
                return {
                    'data': result,
                    'metadata': {
                        'source': 'memory_cache',
                        'fresh': True
                    }
                }
        
        # Try disk cache
        if self.disk_cache:
            result = self.disk_cache.get(key)
            if result is not None:
                # Also store in memory cache for faster access
                if self.memory_cache:
                    self.memory_cache.set(key, result, self.config.memory_cache_ttl)
                
                return {
                    'data': result,
                    'metadata': {
                        'source': 'disk_cache',
                        'fresh': True
                    }
                }
        
        # If use_stale is enabled, try to find expired data
        if use_stale:
            return self._get_stale(key)
        
        return None
    
    def _get_stale(self, key: Union[str, Dict]) -> Optional[Dict[str, Any]]:
        """Get stale data for graceful degradation"""
        # This would require modifying cache implementations to keep expired data
        # For now, return None - could be enhanced later
        return None
    
    def set(self, key: Union[str, Dict], value: Any, 
            memory_ttl: Optional[int] = None, 
            disk_ttl: Optional[int] = None) -> None:
        """Set value in available caches"""
        
        if self.memory_cache:
            self.memory_cache.set(key, value, memory_ttl)
        
        if self.disk_cache:
            self.disk_cache.set(key, value, disk_ttl)
    
    def clear(self) -> None:
        """Clear all caches"""
        if self.memory_cache:
            self.memory_cache.clear()
        
        if self.disk_cache:
            self.disk_cache.clear()
        
        self.logger.info("All caches cleared")
    
    def cleanup(self) -> Dict[str, int]:
        """Cleanup expired entries and return statistics"""
        stats = {}
        
        if self.disk_cache:
            stats['disk_cleanup'] = self.disk_cache.cleanup_expired()
        
        return stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            'memory_cache': None,
            'disk_cache': None,
            'total_hit_rate': 0.0
        }
        
        total_hits = 0
        total_requests = 0
        
        if self.memory_cache:
            memory_stats = self.memory_cache.get_stats()
            stats['memory_cache'] = memory_stats
            total_hits += memory_stats['hits']
            total_requests += memory_stats['hits'] + memory_stats['misses']
        
        if self.disk_cache:
            disk_stats = self.disk_cache.get_stats()
            stats['disk_cache'] = disk_stats
            total_hits += disk_stats['hits']
            total_requests += disk_stats['hits'] + disk_stats['misses']
        
        if total_requests > 0:
            stats['total_hit_rate'] = total_hits / total_requests
        
        return stats