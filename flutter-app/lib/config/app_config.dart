/// Configuration abstraction for environment variables and build-time injection
/// Supports --dart-define for different environments
class AppConfig {
  // Environment detection
  static const String environment = String.fromEnvironment(
    'ENVIRONMENT',
    defaultValue: 'development',
  );

  // API Configuration
  static const String bahnApiBaseUrl = String.fromEnvironment(
    'BAHN_API_BASE_URL',
    defaultValue: 'https://www.bahn.de/web/api',
  );

  // Network settings
  static const int defaultRequestTimeout = int.fromEnvironment(
    'DEFAULT_REQUEST_TIMEOUT',
    defaultValue: 30000, // 30 seconds
  );

  static const int defaultDelayMs = int.fromEnvironment(
    'DEFAULT_DELAY_MS',
    defaultValue: 500,
  );

  // User Agent
  static const String userAgent = String.fromEnvironment(
    'USER_AGENT',
    defaultValue: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  );

  // Logging configuration
  static const String logLevel = String.fromEnvironment(
    'LOG_LEVEL',
    defaultValue: 'info',
  );

  static const bool enableDebugLogs = bool.fromEnvironment(
    'ENABLE_DEBUG_LOGS',
    defaultValue: false,
  );

  // Feature flags
  static const bool enableAdvancedLogging = bool.fromEnvironment(
    'ENABLE_ADVANCED_LOGGING',
    defaultValue: false,
  );

  static const bool enableDebugMenu = bool.fromEnvironment(
    'ENABLE_DEBUG_MENU',
    defaultValue: false,
  );

  // Build information
  static const String buildNumber = String.fromEnvironment(
    'BUILD_NUMBER',
    defaultValue: '1',
  );

  static const String version = String.fromEnvironment(
    'VERSION',
    defaultValue: '1.0.0',
  );

  // Validation helpers
  static bool get isProduction => environment == 'production';
  static bool get isDevelopment => environment == 'development';
  static bool get isStaging => environment == 'staging';
  
  // Computed configuration
  static bool get shouldShowLogs => isDevelopment || enableDebugLogs;
  static bool get shouldShowDebugMenu => isDevelopment || enableDebugMenu;

  /// Get configuration summary for debugging
  static Map<String, dynamic> getConfigSummary() {
    return {
      'environment': environment,
      'bahnApiBaseUrl': bahnApiBaseUrl,
      'defaultRequestTimeout': defaultRequestTimeout,
      'defaultDelayMs': defaultDelayMs,
      'logLevel': logLevel,
      'enableDebugLogs': enableDebugLogs,
      'enableAdvancedLogging': enableAdvancedLogging,
      'enableDebugMenu': enableDebugMenu,
      'buildNumber': buildNumber,
      'version': version,
      'isProduction': isProduction,
      'isDevelopment': isDevelopment,
      'isStaging': isStaging,
    };
  }

  /// Validate configuration at startup
  static bool validateConfig() {
    if (bahnApiBaseUrl.isEmpty) {
      throw Exception('BAHN_API_BASE_URL cannot be empty');
    }
    
    if (defaultRequestTimeout < 1000) {
      throw Exception('DEFAULT_REQUEST_TIMEOUT must be at least 1000ms');
    }

    if (!['development', 'staging', 'production'].contains(environment)) {
      throw Exception('ENVIRONMENT must be one of: development, staging, production');
    }

    return true;
  }
}