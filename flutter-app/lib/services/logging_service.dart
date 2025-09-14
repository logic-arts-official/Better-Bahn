import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import '../config/app_config.dart';

/// Structured logging service that respects privacy and environment settings
/// Provides different log levels and filtering based on environment
class LoggingService {
  static const String _tag = 'BetterBahn';
  
  // Private constructor to prevent instantiation
  LoggingService._();
  
  /// Log levels following standard practice
  enum LogLevel {
    debug(0, 'DEBUG'),
    info(1, 'INFO'),
    warning(2, 'WARN'),
    error(3, 'ERROR'),
    fatal(4, 'FATAL');
    
    const LogLevel(this.value, this.name);
    final int value;
    final String name;
  }
  
  static LogLevel get _currentLogLevel {
    switch (AppConfig.logLevel.toLowerCase()) {
      case 'debug':
        return LogLevel.debug;
      case 'info':
        return LogLevel.info;
      case 'warning':
      case 'warn':
        return LogLevel.warning;
      case 'error':
        return LogLevel.error;
      case 'fatal':
        return LogLevel.fatal;
      default:
        return LogLevel.info;
    }
  }
  
  /// Check if a log level should be output
  static bool _shouldLog(LogLevel level) {
    if (kReleaseMode && !AppConfig.enableDebugLogs) {
      // In release mode, only log warnings and above unless explicitly enabled
      return level.value >= LogLevel.warning.value;
    }
    
    return level.value >= _currentLogLevel.value;
  }
  
  /// Format log message with timestamp and level
  static String _formatMessage(LogLevel level, String message, {
    String? tag,
    Map<String, dynamic>? metadata,
  }) {
    final now = DateTime.now().toIso8601String();
    final logTag = tag ?? _tag;
    
    var formattedMessage = '[$now] [${level.name}] [$logTag] $message';
    
    if (metadata != null && metadata.isNotEmpty) {
      final metadataStr = metadata.entries
          .map((e) => '${e.key}=${e.value}')
          .join(', ');
      formattedMessage += ' | Metadata: {$metadataStr}';
    }
    
    return formattedMessage;
  }
  
  /// Sanitize sensitive data from logs
  static String _sanitizeMessage(String message) {
    // Remove potential PII patterns
    var sanitized = message;
    
    // Sanitize potential personal identifiers (simplified regex patterns)
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\b'),
      (match) => '<TIMESTAMP>',
    );
    
    // Sanitize potential API keys or tokens in URLs
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'(\?|&)(vbid|token|key|auth)=([^&\s]+)', caseSensitive: false),
      (match) => '${match.group(1)}${match.group(2)}=<REDACTED>',
    );
    
    // Sanitize email-like patterns
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
      (match) => '<EMAIL>',
    );
    
    return sanitized;
  }
  
  /// Log debug messages
  static void debug(String message, {
    String? tag,
    Map<String, dynamic>? metadata,
  }) {
    if (!_shouldLog(LogLevel.debug)) return;
    
    final sanitizedMessage = _sanitizeMessage(message);
    final formattedMessage = _formatMessage(
      LogLevel.debug,
      sanitizedMessage,
      tag: tag,
      metadata: metadata,
    );
    
    if (kDebugMode) {
      developer.log(
        formattedMessage,
        name: tag ?? _tag,
        level: 500, // Debug level
      );
    }
  }
  
  /// Log info messages
  static void info(String message, {
    String? tag,
    Map<String, dynamic>? metadata,
  }) {
    if (!_shouldLog(LogLevel.info)) return;
    
    final sanitizedMessage = _sanitizeMessage(message);
    final formattedMessage = _formatMessage(
      LogLevel.info,
      sanitizedMessage,
      tag: tag,
      metadata: metadata,
    );
    
    developer.log(
      formattedMessage,
      name: tag ?? _tag,
      level: 800, // Info level
    );
  }
  
  /// Log warning messages
  static void warning(String message, {
    String? tag,
    Map<String, dynamic>? metadata,
  }) {
    if (!_shouldLog(LogLevel.warning)) return;
    
    final sanitizedMessage = _sanitizeMessage(message);
    final formattedMessage = _formatMessage(
      LogLevel.warning,
      sanitizedMessage,
      tag: tag,
      metadata: metadata,
    );
    
    developer.log(
      formattedMessage,
      name: tag ?? _tag,
      level: 900, // Warning level
    );
  }
  
  /// Log error messages
  static void error(String message, {
    String? tag,
    Map<String, dynamic>? metadata,
    Object? error,
    StackTrace? stackTrace,
  }) {
    if (!_shouldLog(LogLevel.error)) return;
    
    final sanitizedMessage = _sanitizeMessage(message);
    final formattedMessage = _formatMessage(
      LogLevel.error,
      sanitizedMessage,
      tag: tag,
      metadata: metadata,
    );
    
    developer.log(
      formattedMessage,
      name: tag ?? _tag,
      level: 1000, // Error level
      error: error,
      stackTrace: stackTrace,
    );
  }
  
  /// Log fatal messages
  static void fatal(String message, {
    String? tag,
    Map<String, dynamic>? metadata,
    Object? error,
    StackTrace? stackTrace,
  }) {
    final sanitizedMessage = _sanitizeMessage(message);
    final formattedMessage = _formatMessage(
      LogLevel.fatal,
      sanitizedMessage,
      tag: tag,
      metadata: metadata,
    );
    
    developer.log(
      formattedMessage,
      name: tag ?? _tag,
      level: 1200, // Fatal level
      error: error,
      stackTrace: stackTrace,
    );
  }
  
  /// Network request logging
  static void logNetworkRequest({
    required String method,
    required String url,
    Map<String, String>? headers,
    String? body,
    int? statusCode,
    String? responseTime,
  }) {
    if (!AppConfig.enableAdvancedLogging) return;
    
    final metadata = <String, dynamic>{
      'method': method,
      'url': _sanitizeMessage(url),
      if (statusCode != null) 'statusCode': statusCode,
      if (responseTime != null) 'responseTime': responseTime,
    };
    
    final message = 'Network request: $method ${_sanitizeMessage(url)}';
    
    if (statusCode != null && statusCode >= 400) {
      error(message, metadata: metadata);
    } else {
      debug(message, metadata: metadata);
    }
  }
  
  /// App lifecycle logging
  static void logAppLifecycle(String event, {Map<String, dynamic>? metadata}) {
    info('App lifecycle: $event', metadata: metadata);
  }
  
  /// Feature usage logging (anonymized)
  static void logFeatureUsage(String feature, {Map<String, dynamic>? metadata}) {
    info('Feature used: $feature', metadata: metadata);
  }
}