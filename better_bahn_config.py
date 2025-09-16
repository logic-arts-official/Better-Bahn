"""
Configuration management for Better-Bahn real-time API integration.
Supports environment variables and config files for flexible deployment.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from pathlib import Path


@dataclass
class APIConfig:
    """Configuration for API clients"""
    base_url: str = "https://v6.db.transport.rest"
    timeout: int = 30
    rate_limit_delay: float = 0.2
    max_retries: int = 3
    user_agent: str = "Better-Bahn/1.0"
    
    # Rate limiting configuration
    exponential_backoff: bool = True
    max_backoff_delay: float = 60.0
    respect_retry_after: bool = True
    
    # Feature flags
    enable_realtime: bool = True


@dataclass
class CacheConfig:
    """Configuration for caching layer"""
    enable_memory_cache: bool = True
    memory_cache_ttl: int = 30  # seconds
    memory_cache_max_size: int = 1000
    
    enable_disk_cache: bool = False
    disk_cache_ttl: int = 300  # seconds
    disk_cache_dir: str = "/tmp/better_bahn_cache"


@dataclass
class LoggingConfig:
    """Configuration for logging and metrics"""
    enable_metrics: bool = True
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Metrics configuration
    track_latency: bool = True
    track_status_codes: bool = True
    track_cache_hits: bool = True


@dataclass
class BetterBahnConfig:
    """Main configuration class for Better-Bahn"""
    api: APIConfig = field(default_factory=APIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # CLI defaults
    default_age: int = 30
    default_bahncard: Optional[str] = None
    default_deutschland_ticket: bool = False
    
    @classmethod
    def from_env(cls) -> 'BetterBahnConfig':
        """Load configuration from environment variables"""
        
        # API configuration
        api_config = APIConfig(
            base_url=os.getenv('BETTER_BAHN_API_URL', APIConfig.base_url),
            timeout=int(os.getenv('BETTER_BAHN_TIMEOUT', APIConfig.timeout)),
            rate_limit_delay=float(os.getenv('BETTER_BAHN_RATE_LIMIT', APIConfig.rate_limit_delay)),
            max_retries=int(os.getenv('BETTER_BAHN_MAX_RETRIES', APIConfig.max_retries)),
            user_agent=os.getenv('BETTER_BAHN_USER_AGENT', APIConfig.user_agent),
            exponential_backoff=os.getenv('BETTER_BAHN_EXPONENTIAL_BACKOFF', 'true').lower() == 'true',
            max_backoff_delay=float(os.getenv('BETTER_BAHN_MAX_BACKOFF', APIConfig.max_backoff_delay)),
            respect_retry_after=os.getenv('BETTER_BAHN_RESPECT_RETRY_AFTER', 'true').lower() == 'true',
            enable_realtime=os.getenv('BETTER_BAHN_ENABLE_REALTIME', 'true').lower() == 'true'
        )
        
        # Cache configuration
        cache_config = CacheConfig(
            enable_memory_cache=os.getenv('BETTER_BAHN_MEMORY_CACHE', 'true').lower() == 'true',
            memory_cache_ttl=int(os.getenv('BETTER_BAHN_MEMORY_CACHE_TTL', CacheConfig.memory_cache_ttl)),
            memory_cache_max_size=int(os.getenv('BETTER_BAHN_MEMORY_CACHE_SIZE', CacheConfig.memory_cache_max_size)),
            enable_disk_cache=os.getenv('BETTER_BAHN_DISK_CACHE', 'false').lower() == 'true',
            disk_cache_ttl=int(os.getenv('BETTER_BAHN_DISK_CACHE_TTL', CacheConfig.disk_cache_ttl)),
            disk_cache_dir=os.getenv('BETTER_BAHN_DISK_CACHE_DIR', CacheConfig.disk_cache_dir)
        )
        
        # Logging configuration
        logging_config = LoggingConfig(
            enable_metrics=os.getenv('BETTER_BAHN_METRICS', 'true').lower() == 'true',
            log_level=os.getenv('BETTER_BAHN_LOG_LEVEL', LoggingConfig.log_level),
            log_format=os.getenv('BETTER_BAHN_LOG_FORMAT', LoggingConfig.log_format),
            track_latency=os.getenv('BETTER_BAHN_TRACK_LATENCY', 'true').lower() == 'true',
            track_status_codes=os.getenv('BETTER_BAHN_TRACK_STATUS', 'true').lower() == 'true',
            track_cache_hits=os.getenv('BETTER_BAHN_TRACK_CACHE', 'true').lower() == 'true'
        )
        
        return cls(
            api=api_config,
            cache=cache_config,
            logging=logging_config,
            default_age=int(os.getenv('BETTER_BAHN_DEFAULT_AGE', 30)),
            default_bahncard=os.getenv('BETTER_BAHN_DEFAULT_BAHNCARD'),
            default_deutschland_ticket=os.getenv('BETTER_BAHN_DEFAULT_DEUTSCHLAND_TICKET', 'false').lower() == 'true'
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'BetterBahnConfig':
        """Load configuration from JSON file"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse API configuration
        api_data = data.get('api', {})
        api_config = APIConfig(
            base_url=api_data.get('base_url', APIConfig.base_url),
            timeout=api_data.get('timeout', APIConfig.timeout),
            rate_limit_delay=api_data.get('rate_limit_delay', APIConfig.rate_limit_delay),
            max_retries=api_data.get('max_retries', APIConfig.max_retries),
            user_agent=api_data.get('user_agent', APIConfig.user_agent),
            exponential_backoff=api_data.get('exponential_backoff', APIConfig.exponential_backoff),
            max_backoff_delay=api_data.get('max_backoff_delay', APIConfig.max_backoff_delay),
            respect_retry_after=api_data.get('respect_retry_after', APIConfig.respect_retry_after),
            enable_realtime=api_data.get('enable_realtime', APIConfig.enable_realtime)
        )
        
        # Parse cache configuration
        cache_data = data.get('cache', {})
        cache_config = CacheConfig(
            enable_memory_cache=cache_data.get('enable_memory_cache', CacheConfig.enable_memory_cache),
            memory_cache_ttl=cache_data.get('memory_cache_ttl', CacheConfig.memory_cache_ttl),
            memory_cache_max_size=cache_data.get('memory_cache_max_size', CacheConfig.memory_cache_max_size),
            enable_disk_cache=cache_data.get('enable_disk_cache', CacheConfig.enable_disk_cache),
            disk_cache_ttl=cache_data.get('disk_cache_ttl', CacheConfig.disk_cache_ttl),
            disk_cache_dir=cache_data.get('disk_cache_dir', CacheConfig.disk_cache_dir)
        )
        
        # Parse logging configuration
        logging_data = data.get('logging', {})
        logging_config = LoggingConfig(
            enable_metrics=logging_data.get('enable_metrics', LoggingConfig.enable_metrics),
            log_level=logging_data.get('log_level', LoggingConfig.log_level),
            log_format=logging_data.get('log_format', LoggingConfig.log_format),
            track_latency=logging_data.get('track_latency', LoggingConfig.track_latency),
            track_status_codes=logging_data.get('track_status_codes', LoggingConfig.track_status_codes),
            track_cache_hits=logging_data.get('track_cache_hits', LoggingConfig.track_cache_hits)
        )
        
        return cls(
            api=api_config,
            cache=cache_config,
            logging=logging_config,
            default_age=data.get('default_age', 30),
            default_bahncard=data.get('default_bahncard'),
            default_deutschland_ticket=data.get('default_deutschland_ticket', False)
        )
    
    def to_file(self, config_path: str) -> None:
        """Save configuration to JSON file"""
        data = {
            'api': {
                'base_url': self.api.base_url,
                'timeout': self.api.timeout,
                'rate_limit_delay': self.api.rate_limit_delay,
                'max_retries': self.api.max_retries,
                'user_agent': self.api.user_agent,
                'exponential_backoff': self.api.exponential_backoff,
                'max_backoff_delay': self.api.max_backoff_delay,
                'respect_retry_after': self.api.respect_retry_after,
                'enable_realtime': self.api.enable_realtime
            },
            'cache': {
                'enable_memory_cache': self.cache.enable_memory_cache,
                'memory_cache_ttl': self.cache.memory_cache_ttl,
                'memory_cache_max_size': self.cache.memory_cache_max_size,
                'enable_disk_cache': self.cache.enable_disk_cache,
                'disk_cache_ttl': self.cache.disk_cache_ttl,
                'disk_cache_dir': self.cache.disk_cache_dir
            },
            'logging': {
                'enable_metrics': self.logging.enable_metrics,
                'log_level': self.logging.log_level,
                'log_format': self.logging.log_format,
                'track_latency': self.logging.track_latency,
                'track_status_codes': self.logging.track_status_codes,
                'track_cache_hits': self.logging.track_cache_hits
            },
            'default_age': self.default_age,
            'default_bahncard': self.default_bahncard,
            'default_deutschland_ticket': self.default_deutschland_ticket
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def setup_logging(self):
        """Setup logging configuration"""
        logger = logging.getLogger('better_bahn')
        logger.setLevel(getattr(logging, self.logging.log_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, self.logging.log_level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(self.logging.log_format)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger


# Default configuration instance
default_config = BetterBahnConfig.from_env()