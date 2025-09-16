/// Masterdata Validation Service for Better-Bahn Flutter App
/// 
/// This service provides validation capabilities for station and service data
/// during development and runtime, complementing the Python validation functions.
/// 
/// Validates against the same schema structure as the Python backend.

import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;

/// Station data validation and processing
class StationData {
  final String id;
  final String name;
  final String nameNormalized;
  final int? eva;
  final double? lat;
  final double? lon;
  final String? ds100;
  final List<String>? platforms;
  final Map<String, dynamic>? externalIds;
  final Map<String, dynamic>? metadata;

  const StationData({
    required this.id,
    required this.name,
    required this.nameNormalized,
    this.eva,
    this.lat,
    this.lon,
    this.ds100,
    this.platforms,
    this.externalIds,
    this.metadata,
  });

  factory StationData.fromJson(Map<String, dynamic> json) {
    return StationData(
      id: json['id'] as String,
      name: json['name'] as String,
      nameNormalized: json['name_normalized'] as String,
      eva: json['eva'] as int?,
      lat: json['lat'] as double?,
      lon: json['lon'] as double?,
      ds100: json['ds100'] as String?,
      platforms: (json['platforms'] as List<dynamic>?)?.cast<String>(),
      externalIds: json['external_ids'] as Map<String, dynamic>?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = {
      'id': id,
      'name': name,
      'name_normalized': nameNormalized,
    };
    
    if (eva != null) data['eva'] = eva;
    if (lat != null) data['lat'] = lat;
    if (lon != null) data['lon'] = lon;
    if (ds100 != null) data['ds100'] = ds100;
    if (platforms != null) data['platforms'] = platforms;
    if (externalIds != null) data['external_ids'] = externalIds;
    if (metadata != null) data['metadata'] = metadata;
    
    return data;
  }
}

/// Service stop data
class ServiceStop {
  final String stationId;
  final int sequence;
  final String? arrivalPlanned;
  final String? departurePlanned;
  final String? platform;
  final String? stopType;
  final List<Map<String, String>>? attributes;

  const ServiceStop({
    required this.stationId,
    required this.sequence,
    this.arrivalPlanned,
    this.departurePlanned,
    this.platform,
    this.stopType,
    this.attributes,
  });

  factory ServiceStop.fromJson(Map<String, dynamic> json) {
    return ServiceStop(
      stationId: json['station_id'] as String,
      sequence: json['sequence'] as int,
      arrivalPlanned: json['arrival_planned'] as String?,
      departurePlanned: json['departure_planned'] as String?,
      platform: json['platform'] as String?,
      stopType: json['stop_type'] as String?,
      attributes: (json['attributes'] as List<dynamic>?)
          ?.map((attr) => Map<String, String>.from(attr as Map))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = {
      'station_id': stationId,
      'sequence': sequence,
    };
    
    if (arrivalPlanned != null) data['arrival_planned'] = arrivalPlanned;
    if (departurePlanned != null) data['departure_planned'] = departurePlanned;
    if (platform != null) data['platform'] = platform;
    if (stopType != null) data['stop_type'] = stopType;
    if (attributes != null) data['attributes'] = attributes;
    
    return data;
  }
}

/// Service/Trip data
class ServiceData {
  final String id;
  final String? tripId;
  final String? line;
  final String? operator;
  final String product;
  final List<ServiceStop> stops;
  final Map<String, bool> operatingDays;
  final Map<String, String>? dateRange;
  final List<Map<String, String>>? attributes;

  const ServiceData({
    required this.id,
    this.tripId,
    this.line,
    this.operator,
    required this.product,
    required this.stops,
    required this.operatingDays,
    this.dateRange,
    this.attributes,
  });

  factory ServiceData.fromJson(Map<String, dynamic> json) {
    final operatingDaysJson = json['operating_days'] as Map<String, dynamic>;
    return ServiceData(
      id: json['id'] as String,
      tripId: json['trip_id'] as String?,
      line: json['line'] as String?,
      operator: json['operator'] as String?,
      product: json['product'] as String,
      stops: (json['stops'] as List<dynamic>)
          .map((stop) => ServiceStop.fromJson(stop as Map<String, dynamic>))
          .toList(),
      operatingDays: {
        'monday': operatingDaysJson['monday'] as bool,
        'tuesday': operatingDaysJson['tuesday'] as bool,
        'wednesday': operatingDaysJson['wednesday'] as bool,
        'thursday': operatingDaysJson['thursday'] as bool,
        'friday': operatingDaysJson['friday'] as bool,
        'saturday': operatingDaysJson['saturday'] as bool,
        'sunday': operatingDaysJson['sunday'] as bool,
      },
      dateRange: operatingDaysJson['date_range'] != null
          ? Map<String, String>.from(operatingDaysJson['date_range'] as Map)
          : null,
      attributes: (json['attributes'] as List<dynamic>?)
          ?.map((attr) => Map<String, String>.from(attr as Map))
          .toList(),
    );
  }
}

/// Validation result for data validation operations
class ValidationResult {
  final bool isValid;
  final List<String> errors;
  final List<String> warnings;

  const ValidationResult({
    required this.isValid,
    required this.errors,
    this.warnings = const [],
  });

  ValidationResult.valid() : this(isValid: true, errors: []);
  
  ValidationResult.invalid(List<String> errors, [List<String>? warnings])
      : this(isValid: false, errors: errors, warnings: warnings ?? []);
}

/// Masterdata validation service
class MasterdataValidationService {
  static const List<String> validProducts = [
    'ICE', 'IC', 'EC', 'RE', 'RB', 'S', 'U', 'TRAM', 'BUS'
  ];

  static const List<String> validStopTypes = [
    'boarding_only', 'alighting_only', 'boarding_alighting', 'pass_through'
  ];

  /// Normalize station name for search index
  /// Dart implementation of the Python normalize_station_name function
  static String normalizeStationName(String name) {
    if (name.isEmpty) return '';

    // Basic normalization - Dart doesn't have full Unicode normalization
    // This is a simplified version for development validation
    String normalized = name.toLowerCase();
    
    // Replace common German umlauts and special characters
    normalized = normalized
        .replaceAll('ä', 'a')
        .replaceAll('ö', 'o')
        .replaceAll('ü', 'u')
        .replaceAll('ß', 'ss')
        .replaceAll('é', 'e')
        .replaceAll('è', 'e')
        .replaceAll('ê', 'e')
        .replaceAll('à', 'a')
        .replaceAll('á', 'a')
        .replaceAll('â', 'a')
        .replaceAll('ç', 'c');
    
    // Normalize whitespace
    normalized = normalized.replaceAll(RegExp(r'\s+'), ' ').trim();
    
    return normalized;
  }

  /// Validate EVA number format
  static bool validateEvaNumber(int eva) {
    return eva >= 1000000 && eva <= 9999999;
  }

  /// Validate coordinates for German railway stations
  static ValidationResult validateCoordinates(double? lat, double? lon) {
    final errors = <String>[];
    
    if (lat != null && lon != null) {
      // Germany is approximately between 47-55°N, 6-15°E
      if (lat < 47 || lat > 55) {
        errors.add('Latitude outside German range: $lat');
      }
      if (lon < 6 || lon > 15) {
        errors.add('Longitude outside German range: $lon');
      }
    }
    
    return errors.isEmpty 
        ? ValidationResult.valid()
        : ValidationResult.invalid(errors);
  }

  /// Validate station data
  static ValidationResult validateStationData(StationData station) {
    final errors = <String>[];
    final warnings = <String>[];

    // Required fields
    if (station.id.isEmpty) {
      errors.add('Station ID is required');
    }
    if (station.name.isEmpty) {
      errors.add('Station name is required');
    }
    if (station.nameNormalized.isEmpty) {
      errors.add('Normalized station name is required');
    }

    // Validate ID format
    if (!RegExp(r'^[0-9A-Za-z_-]+$').hasMatch(station.id)) {
      errors.add('Invalid station ID format: ${station.id}');
    }

    // Validate EVA number if present
    if (station.eva != null && !validateEvaNumber(station.eva!)) {
      errors.add('Invalid EVA number: ${station.eva}');
    }

    // Validate coordinates
    final coordValidation = validateCoordinates(station.lat, station.lon);
    errors.addAll(coordValidation.errors);

    // Validate DS100 format if present
    if (station.ds100 != null && 
        !RegExp(r'^[A-Z0-9 ]+$').hasMatch(station.ds100!)) {
      errors.add('Invalid DS100 format: ${station.ds100}');
    }

    // Check if normalized name matches expected result
    final expectedNormalized = normalizeStationName(station.name);
    if (station.nameNormalized != expectedNormalized) {
      warnings.add('Normalized name mismatch: expected "$expectedNormalized", got "${station.nameNormalized}"');
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
      warnings: warnings,
    );
  }

  /// Validate service data
  static ValidationResult validateServiceData(ServiceData service) {
    final errors = <String>[];
    final warnings = <String>[];

    // Required fields
    if (service.id.isEmpty) {
      errors.add('Service ID is required');
    }
    if (!validProducts.contains(service.product)) {
      errors.add('Invalid product: ${service.product}');
    }
    if (service.stops.length < 2) {
      errors.add('Service must have at least 2 stops');
    }

    // Validate ID format
    if (!RegExp(r'^[0-9A-Za-z_-]+$').hasMatch(service.id)) {
      errors.add('Invalid service ID format: ${service.id}');
    }

    // Validate stop sequence
    for (int i = 0; i < service.stops.length; i++) {
      final stop = service.stops[i];
      if (stop.sequence != i) {
        errors.add('Stop sequence mismatch: expected $i, got ${stop.sequence}');
      }
      
      // Validate stop type if present
      if (stop.stopType != null && !validStopTypes.contains(stop.stopType)) {
        errors.add('Invalid stop type: ${stop.stopType}');
      }
      
      // Validate time formats
      if (stop.arrivalPlanned != null) {
        if (!_isValidISODateTime(stop.arrivalPlanned!)) {
          errors.add('Invalid arrival time format: ${stop.arrivalPlanned}');
        }
      }
      if (stop.departurePlanned != null) {
        if (!_isValidISODateTime(stop.departurePlanned!)) {
          errors.add('Invalid departure time format: ${stop.departurePlanned}');
        }
      }
      
      // Check departure after arrival
      if (stop.arrivalPlanned != null && stop.departurePlanned != null) {
        try {
          final arrival = DateTime.parse(stop.arrivalPlanned!);
          final departure = DateTime.parse(stop.departurePlanned!);
          if (departure.isBefore(arrival)) {
            errors.add('Departure before arrival in stop ${stop.sequence}');
          }
        } catch (e) {
          // Already caught by format validation above
        }
      }
    }

    return ValidationResult(
      isValid: errors.isEmpty,
      errors: errors,
      warnings: warnings,
    );
  }

  /// Validate ISO 8601 datetime format
  static bool _isValidISODateTime(String dateTimeString) {
    try {
      DateTime.parse(dateTimeString);
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Development validation script entry point
  static Future<void> runDevValidation() async {
    print('🚀 Better-Bahn Masterdata Validation (Dart)');
    print('===========================================');
    
    // Test station data validation
    print('\n📍 Testing Station Validation:');
    
    final testStation = StationData(
      id: 'TEST_STATION_001',
      name: 'München Hauptbahnhof',
      nameNormalized: normalizeStationName('München Hauptbahnhof'),
      eva: 8000261,
      lat: 48.1400,
      lon: 11.5583,
      ds100: 'MH',
      platforms: ['1', '2', '3', '4'],
      externalIds: {'hafas': 'test_id'},
      metadata: {'state': 'Bayern', 'category': '1'},
    );
    
    final stationValidation = validateStationData(testStation);
    print('Station validation: ${stationValidation.isValid ? "✅ VALID" : "❌ INVALID"}');
    if (stationValidation.errors.isNotEmpty) {
      print('Errors: ${stationValidation.errors.join(", ")}');
    }
    if (stationValidation.warnings.isNotEmpty) {
      print('Warnings: ${stationValidation.warnings.join(", ")}');
    }
    
    // Test service data validation
    print('\n🚆 Testing Service Validation:');
    
    final testService = ServiceData(
      id: 'ICE_123_20240101',
      tripId: 'trip_123',
      line: 'ICE 123',
      operator: 'DB Fernverkehr AG',
      product: 'ICE',
      stops: [
        ServiceStop(
          stationId: 'TEST_STATION_001',
          sequence: 0,
          departurePlanned: '2024-01-01T08:00:00Z',
          platform: '1',
          stopType: 'boarding_only',
        ),
        ServiceStop(
          stationId: 'TEST_STATION_002', 
          sequence: 1,
          arrivalPlanned: '2024-01-01T10:00:00Z',
          platform: '2',
          stopType: 'alighting_only',
        ),
      ],
      operatingDays: {
        'monday': true,
        'tuesday': true,
        'wednesday': true,
        'thursday': true,
        'friday': true,
        'saturday': false,
        'sunday': false,
      },
      dateRange: {
        'start': '2024-01-01',
        'end': '2024-12-31',
      },
    );
    
    final serviceValidation = validateServiceData(testService);
    print('Service validation: ${serviceValidation.isValid ? "✅ VALID" : "❌ INVALID"}');
    if (serviceValidation.errors.isNotEmpty) {
      print('Errors: ${serviceValidation.errors.join(", ")}');
    }
    if (serviceValidation.warnings.isNotEmpty) {
      print('Warnings: ${serviceValidation.warnings.join(", ")}');
    }
    
    // Test normalization
    print('\n🔤 Testing Name Normalization:');
    final testNames = [
      'München Hauptbahnhof',
      'Köln Hbf',
      'Düsseldorf Flughafen',
      'Würzburg Hbf',
      'Bahnhof François Mitterrand',
    ];
    
    for (final name in testNames) {
      final normalized = normalizeStationName(name);
      print('$name → $normalized');
    }
    
    print('\n✅ Development validation completed!');
  }
}

/// Main function for running as a standalone script
void main() async {
  await MasterdataValidationService.runDevValidation();
}