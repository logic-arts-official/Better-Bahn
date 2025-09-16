/// Masterdata loader service for Flutter app.
/// 
/// Provides functionality to load, validate, and manage strongly typed
/// masterdata objects with proper error handling and caching for the Flutter app.

import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import '../models/masterdata_models.dart';

/// Custom exception for masterdata validation errors.
class MasterdataValidationException implements Exception {
  final String message;
  const MasterdataValidationException(this.message);
  
  @override
  String toString() => 'MasterdataValidationException: $message';
}

/// Masterdata loader service for Flutter.
class MasterdataLoaderService {
  static const String _defaultAssetPath = 'assets/data/Timetables-1.0.213.yaml';
  
  TimetableMasterdata? _cachedMasterdata;
  Map<String, dynamic>? _cachedSchema;

  /// Load masterdata from assets bundle.
  Future<TimetableMasterdata> loadTimetableMasterdata({
    String assetPath = _defaultAssetPath,
  }) async {
    try {
      // Check if already cached
      if (_cachedMasterdata != null) {
        return _cachedMasterdata!;
      }

      // Load YAML file from assets
      String yamlContent;
      try {
        yamlContent = await rootBundle.loadString(assetPath);
      } catch (e) {
        throw MasterdataValidationException(
          'Masterdata file not found: $assetPath. '
          'Please ensure the file exists in the assets bundle.'
        );
      }

      if (yamlContent.trim().isEmpty) {
        throw MasterdataValidationException(
          'YAML file $assetPath is empty or contains only whitespace.'
        );
      }

      // Parse YAML (simplified - in a real app you'd use a YAML parser)
      // For now, we assume the YAML is converted to JSON format in assets
      Map<String, dynamic> rawData;
      try {
        // Try to parse as JSON first (assuming pre-converted)
        rawData = jsonDecode(yamlContent) as Map<String, dynamic>;
      } catch (e) {
        // If that fails, throw a helpful error
        throw MasterdataValidationException(
          'Failed to parse YAML file $assetPath. '
          'Please ensure the file contains valid YAML/JSON syntax: $e'
        );
      }

      // Validate basic structure
      if (!rawData.containsKey('info')) {
        throw MasterdataValidationException(
          'Missing required "info" section in masterdata file.'
        );
      }

      if (!rawData.containsKey('components')) {
        throw MasterdataValidationException(
          'Missing required "components" section in masterdata file.'
        );
      }

      // Create strongly typed masterdata object
      final masterdata = TimetableMasterdata.fromJson(rawData);

      // Additional validation
      _validateMasterdataCompleteness(masterdata);

      // Cache the result
      _cachedMasterdata = masterdata;

      // Log successful loading
      debugPrint('✓ Timetable masterdata loaded successfully');
      debugPrint('  Version: ${masterdata.info.version}');
      debugPrint('  Title: ${masterdata.info.title}');
      debugPrint('  SHA256: ${masterdata.dataHash}');
      final summary = masterdata.getSchemaSummary();
      final availableSchemas = summary['availableSchemas'] as Map<String, dynamic>;
      final schemasCount = availableSchemas.values.where((v) => v == true).length;
      debugPrint('  Schemas available: $schemasCount/6');

      return masterdata;

    } catch (e) {
      if (e is MasterdataValidationException) {
        rethrow;
      }
      throw MasterdataValidationException(
        'Unexpected error loading masterdata from $assetPath: $e'
      );
    }
  }

  /// Validate that masterdata contains expected components.
  void _validateMasterdataCompleteness(TimetableMasterdata masterdata) {
    // Check required info fields
    if (masterdata.info.title.isEmpty) {
      throw MasterdataValidationException('API title is missing or empty');
    }

    if (masterdata.info.version.isEmpty) {
      throw MasterdataValidationException('API version is missing or empty');
    }

    // Check OpenAPI version
    if (masterdata.openapiVersion.isEmpty) {
      throw MasterdataValidationException('OpenAPI version is missing');
    }

    // Validate enum schemas contain expected values
    if (masterdata.connectionStatusSchema != null) {
      const expectedStatuses = {'w', 'n', 'a'};
      final actualStatuses = masterdata.connectionStatusSchema!.enumValues.toSet();
      if (!expectedStatuses.isSubset(actualStatuses)) {
        final missing = expectedStatuses.difference(actualStatuses);
        throw MasterdataValidationException(
          'Connection status schema is missing expected values: $missing'
        );
      }
    }

    if (masterdata.delaySourceSchema != null) {
      const expectedSources = {'L', 'NA', 'NM', 'V', 'IA', 'IM', 'A'};
      final actualSources = masterdata.delaySourceSchema!.enumValues.toSet();
      if (!expectedSources.isSubset(actualSources)) {
        final missing = expectedSources.difference(actualSources);
        throw MasterdataValidationException(
          'Delay source schema is missing expected values: $missing'
        );
      }
    }
  }

  /// Get cached masterdata if available.
  TimetableMasterdata? getCachedMasterdata() {
    return _cachedMasterdata;
  }

  /// Force reload masterdata, bypassing cache.
  Future<TimetableMasterdata> reloadMasterdata({
    String assetPath = _defaultAssetPath,
  }) async {
    _cachedMasterdata = null;
    _cachedSchema = null;
    return loadTimetableMasterdata(assetPath: assetPath);
  }

  /// Validate connection data against loaded schemas.
  ConnectionValidationResult validateConnectionData(
    Map<String, dynamic> connectionData,
  ) {
    if (_cachedMasterdata == null) {
      return ConnectionValidationResult.invalid({
        'loader': 'No masterdata loaded. Call loadTimetableMasterdata() first.'
      });
    }

    return _cachedMasterdata!.validateConnectionData(connectionData);
  }

  /// Get a summary of the loaded masterdata.
  Map<String, dynamic>? getMasterdataSummary() {
    return _cachedMasterdata?.getSchemaSummary();
  }

  /// Check if masterdata is loaded and valid.
  bool get isMasterdataLoaded => _cachedMasterdata != null;

  /// Get the data hash for traceability.
  String? get dataHash => _cachedMasterdata?.dataHash;

  /// Clear cached data (useful for testing or memory management).
  void clearCache() {
    _cachedMasterdata = null;
    _cachedSchema = null;
  }
}

// Extension for Set operations (if not available in current Dart version)
extension SetExtension<T> on Set<T> {
  bool isSubset(Set<T> other) {
    return every(other.contains);
  }
}

/// Global singleton instance for easy access throughout the app.
final masterdataService = MasterdataLoaderService();

/// Debug print function that only prints in debug mode.
void debugPrint(String message) {
  if (kDebugMode) {
    print('[MasterdataLoader] $message');
  }
}

/// Check if we're in debug mode.
bool get kDebugMode {
  return !kReleaseMode;
}