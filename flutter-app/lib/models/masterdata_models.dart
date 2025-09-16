/// Dart models for Deutsche Bahn Timetables API masterdata with null-safety.
/// 
/// This provides strongly typed Dart objects for parsing and validating
/// timetable masterdata with proper null-safety and immutable data structures.

import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';

/// Connection status enumeration.
enum ConnectionStatus {
  waiting('w'),       // This connection is waiting
  transition('n'),    // This connection CANNOT wait
  alternative('a');   // Alternative connection

  const ConnectionStatus(this.value);
  final String value;

  static ConnectionStatus? fromString(String? value) {
    return ConnectionStatus.values
        .where((status) => status.value == value)
        .firstOrNull;
  }
}

/// Delay source enumeration.
enum DelaySource {
  leibit('L'),        // LeiBit/LeiDis
  risneAut('NA'),     // IRIS-NE (automatisch)
  risneMan('NM'),     // IRIS-NE (manuell)
  vdv('V'),           // Prognosen durch dritte EVU über VDVin
  istpAut('IA'),      // ISTP automatisch
  istpMan('IM'),      // ISTP manuell
  automatic('A');     // Automatische Prognose

  const DelaySource(this.value);
  final String value;

  static DelaySource? fromString(String? value) {
    return DelaySource.values
        .where((source) => source.value == value)
        .firstOrNull;
  }
}

/// API information from the info section.
class ApiInfo {
  final String title;
  final String version;
  final String? description;
  final String? contactEmail;
  final String? termsOfService;
  final String? xIbmName;

  const ApiInfo({
    required this.title,
    required this.version,
    this.description,
    this.contactEmail,
    this.termsOfService,
    this.xIbmName,
  });

  factory ApiInfo.fromJson(Map<String, dynamic> json) {
    final contact = json['contact'] as Map<String, dynamic>?;
    
    return ApiInfo(
      title: json['title'] as String,
      version: json['version'] as String,
      description: json['description'] as String?,
      contactEmail: contact?['email'] as String?,
      termsOfService: json['termsOfService'] as String?,
      xIbmName: json['x-ibm-name'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'version': version,
      if (description != null) 'description': description,
      if (contactEmail != null) 'contact': {'email': contactEmail},
      if (termsOfService != null) 'termsOfService': termsOfService,
      if (xIbmName != null) 'x-ibm-name': xIbmName,
    };
  }
}

/// Property definition for connection schema.
class ConnectionProperty {
  final String? ref;
  final String? description;
  final String? type;
  final String? format;
  final bool xmlAttribute;

  const ConnectionProperty({
    this.ref,
    this.description,
    this.type,
    this.format,
    this.xmlAttribute = false,
  });

  factory ConnectionProperty.fromJson(Map<String, dynamic> json) {
    final xml = json['xml'] as Map<String, dynamic>?;
    
    return ConnectionProperty(
      ref: json['\$ref'] as String?,
      description: json['description'] as String?,
      type: json['type'] as String?,
      format: json['format'] as String?,
      xmlAttribute: xml?['attribute'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (ref != null) '\$ref': ref,
      if (description != null) 'description': description,
      if (type != null) 'type': type,
      if (format != null) 'format': format,
      if (xmlAttribute) 'xml': {'attribute': xmlAttribute},
    };
  }
}

/// Schema definition for connection objects.
class ConnectionSchema {
  final String description;
  final String type;
  final List<String> required;
  final Map<String, ConnectionProperty> properties;

  const ConnectionSchema({
    required this.description,
    required this.type,
    required this.required,
    required this.properties,
  });

  factory ConnectionSchema.fromJson(Map<String, dynamic> json) {
    final propertiesMap = <String, ConnectionProperty>{};
    final propertiesJson = json['properties'] as Map<String, dynamic>? ?? {};
    
    for (final entry in propertiesJson.entries) {
      propertiesMap[entry.key] = ConnectionProperty.fromJson(
        entry.value as Map<String, dynamic>
      );
    }
    
    return ConnectionSchema(
      description: json['description'] as String? ?? '',
      type: json['type'] as String? ?? 'object',
      required: List<String>.from(json['required'] as List? ?? []),
      properties: propertiesMap,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'description': description,
      'type': type,
      'required': required,
      'properties': properties.map(
        (key, value) => MapEntry(key, value.toJson())
      ),
    };
  }
}

/// Schema definition for enumeration types.
class EnumSchema {
  final String description;
  final String type;
  final List<String> enumValues;

  const EnumSchema({
    required this.description,
    required this.type,
    required this.enumValues,
  });

  factory EnumSchema.fromJson(Map<String, dynamic> json) {
    return EnumSchema(
      description: json['description'] as String? ?? '',
      type: json['type'] as String? ?? 'string',
      enumValues: List<String>.from(json['enum'] as List? ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'description': description,
      'type': type,
      'enum': enumValues,
    };
  }
}

/// Index for fast station lookup.
class StationIndex {
  final Map<int, String> _evaToName;
  final Map<String, int> _nameToEva;
  final Map<String, int> _normalizedNameToEva;

  StationIndex._({
    required Map<int, String> evaToName,
    required Map<String, int> nameToEva,
    required Map<String, int> normalizedNameToEva,
  })  : _evaToName = Map.unmodifiable(evaToName),
        _nameToEva = Map.unmodifiable(nameToEva),
        _normalizedNameToEva = Map.unmodifiable(normalizedNameToEva);

  factory StationIndex.empty() {
    return StationIndex._(
      evaToName: {},
      nameToEva: {},
      normalizedNameToEva: {},
    );
  }

  factory StationIndex.fromStations(Map<int, String> stations) {
    final nameToEva = <String, int>{};
    final normalizedNameToEva = <String, int>{};
    
    for (final entry in stations.entries) {
      final eva = entry.key;
      final name = entry.value;
      
      nameToEva[name] = eva;
      
      // Normalize: lowercase, remove spaces and special chars
      final normalized = name
          .toLowerCase()
          .replaceAll(' ', '')
          .replaceAll('-', '')
          .replaceAll('ü', 'ue')
          .replaceAll('ö', 'oe')
          .replaceAll('ä', 'ae')
          .replaceAll('ß', 'ss');
      normalizedNameToEva[normalized] = eva;
    }
    
    return StationIndex._(
      evaToName: stations,
      nameToEva: nameToEva,
      normalizedNameToEva: normalizedNameToEva,
    );
  }

  /// Lookup EVA number by station name (exact match).
  int? lookupByName(String name) => _nameToEva[name];

  /// Lookup EVA number by normalized station name.
  int? lookupByNormalizedName(String name) {
    final normalized = name
        .toLowerCase()
        .replaceAll(' ', '')
        .replaceAll('-', '')
        .replaceAll('ü', 'ue')
        .replaceAll('ö', 'oe')
        .replaceAll('ä', 'ae')
        .replaceAll('ß', 'ss');
    return _normalizedNameToEva[normalized];
  }

  /// Lookup station name by EVA number.
  String? lookupByEva(int eva) => _evaToName[eva];

  /// Get the number of stations in the index.
  int get size => _evaToName.length;

  /// Get all EVA numbers in the index.
  Iterable<int> get evaNumbers => _evaToName.keys;

  /// Get all station names in the index.
  Iterable<String> get stationNames => _evaToName.values;
}

/// Complete timetable masterdata with strongly typed objects.
class TimetableMasterdata {
  final String openapiVersion;
  final ApiInfo info;
  final ConnectionSchema? connectionSchema;
  final EnumSchema? connectionStatusSchema;
  final EnumSchema? delaySourceSchema;
  final Map<String, dynamic>? distributorMessageSchema;
  final EnumSchema? distributorTypeSchema;
  final Map<String, dynamic>? timetableStopSchema;
  final Map<String, dynamic>? rawData;
  final String? dataHash;
  final StationIndex stationIndex;

  const TimetableMasterdata({
    required this.openapiVersion,
    required this.info,
    this.connectionSchema,
    this.connectionStatusSchema,
    this.delaySourceSchema,
    this.distributorMessageSchema,
    this.distributorTypeSchema,
    this.timetableStopSchema,
    this.rawData,
    this.dataHash,
    required this.stationIndex,
  });

  factory TimetableMasterdata.fromJson(Map<String, dynamic> json) {
    // Extract info
    final infoData = json['info'] as Map<String, dynamic>?;
    if (infoData == null) {
      throw ArgumentError("Missing required 'info' section in masterdata");
    }
    
    final info = ApiInfo.fromJson(infoData);
    
    // Extract schemas
    final components = json['components'] as Map<String, dynamic>? ?? {};
    final schemas = components['schemas'] as Map<String, dynamic>? ?? {};
    
    ConnectionSchema? connectionSchema;
    EnumSchema? connectionStatusSchema;
    EnumSchema? delaySourceSchema;
    EnumSchema? distributorTypeSchema;
    
    if (schemas.containsKey('connection')) {
      connectionSchema = ConnectionSchema.fromJson(
        schemas['connection'] as Map<String, dynamic>
      );
    }
    
    if (schemas.containsKey('connectionStatus')) {
      connectionStatusSchema = EnumSchema.fromJson(
        schemas['connectionStatus'] as Map<String, dynamic>
      );
    }
    
    if (schemas.containsKey('delaySource')) {
      delaySourceSchema = EnumSchema.fromJson(
        schemas['delaySource'] as Map<String, dynamic>
      );
    }
    
    if (schemas.containsKey('distributorType')) {
      distributorTypeSchema = EnumSchema.fromJson(
        schemas['distributorType'] as Map<String, dynamic>
      );
    }
    
    // Calculate data hash for traceability
    final dataJson = jsonEncode(json);
    final bytes = utf8.encode(dataJson);
    final digest = sha256.convert(bytes);
    final dataHash = digest.toString();
    
    // Create station index (would be populated from actual station data if available)
    final stationIndex = StationIndex.empty();
    
    return TimetableMasterdata(
      openapiVersion: json['openapi'] as String? ?? '',
      info: info,
      connectionSchema: connectionSchema,
      connectionStatusSchema: connectionStatusSchema,
      delaySourceSchema: delaySourceSchema,
      distributorMessageSchema: 
          schemas['distributorMessage'] as Map<String, dynamic>?,
      distributorTypeSchema: distributorTypeSchema,
      timetableStopSchema: 
          schemas['timetableStop'] as Map<String, dynamic>?,
      rawData: json,
      dataHash: dataHash,
      stationIndex: stationIndex,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'openapi': openapiVersion,
      'info': info.toJson(),
      if (connectionSchema != null) 
        'connectionSchema': connectionSchema!.toJson(),
      if (connectionStatusSchema != null) 
        'connectionStatusSchema': connectionStatusSchema!.toJson(),
      if (delaySourceSchema != null) 
        'delaySourceSchema': delaySourceSchema!.toJson(),
      if (distributorMessageSchema != null) 
        'distributorMessageSchema': distributorMessageSchema,
      if (distributorTypeSchema != null) 
        'distributorTypeSchema': distributorTypeSchema!.toJson(),
      if (timetableStopSchema != null) 
        'timetableStopSchema': timetableStopSchema,
      if (dataHash != null) 'dataHash': dataHash,
      'stationIndexSize': stationIndex.size,
    };
  }

  /// Validate a connection status value.
  bool validateConnectionStatus(String status) {
    return connectionStatusSchema?.enumValues.contains(status) ?? false;
  }

  /// Validate a delay source value.
  bool validateDelaySource(String source) {
    return delaySourceSchema?.enumValues.contains(source) ?? false;
  }

  /// Validate an EVA station number.
  bool validateEvaNumber(dynamic eva) {
    try {
      final evaInt = eva is String ? int.parse(eva) : eva as int;
      // EVA numbers are typically 6-8 digits
      return evaInt >= 100000 && evaInt <= 99999999;
    } catch (e) {
      return false;
    }
  }

  /// Get a summary of available schemas.
  Map<String, dynamic> getSchemaSummary() {
    return {
      'openapiVersion': openapiVersion,
      'apiTitle': info.title,
      'apiVersion': info.version,
      'dataHash': dataHash,
      'availableSchemas': {
        'connection': connectionSchema != null,
        'connectionStatus': connectionStatusSchema != null,
        'delaySource': delaySourceSchema != null,
        'distributorMessage': distributorMessageSchema != null,
        'distributorType': distributorTypeSchema != null,
        'timetableStop': timetableStopSchema != null,
      },
      'connectionStatusValues': connectionStatusSchema?.enumValues ?? [],
      'delaySourceValues': delaySourceSchema?.enumValues ?? [],
      'stationIndexSize': stationIndex.size,
    };
  }
}

/// Validation result for connection data.
class ConnectionValidationResult {
  final bool isValid;
  final Map<String, String> errors;

  const ConnectionValidationResult({
    required this.isValid,
    required this.errors,
  });

  factory ConnectionValidationResult.valid() {
    return const ConnectionValidationResult(
      isValid: true,
      errors: {},
    );
  }

  factory ConnectionValidationResult.invalid(Map<String, String> errors) {
    return ConnectionValidationResult(
      isValid: false,
      errors: errors,
    );
  }
}

/// Extensions for convenient validation.
extension TimetableMasterdataValidation on TimetableMasterdata {
  /// Validate connection data against loaded schemas.
  ConnectionValidationResult validateConnectionData(
    Map<String, dynamic> connectionData,
  ) {
    final errors = <String, String>{};
    
    // Validate connection status
    if (connectionData.containsKey('cs')) {
      final cs = connectionData['cs'] as String?;
      if (cs != null && !validateConnectionStatus(cs)) {
        final validValues = connectionStatusSchema?.enumValues ?? [];
        errors['cs'] = 
            "Invalid connection status '$cs'. Valid values: $validValues";
      }
    }
    
    // Validate EVA number
    if (connectionData.containsKey('eva')) {
      final eva = connectionData['eva'];
      if (!validateEvaNumber(eva)) {
        errors['eva'] = 
            "Invalid EVA number '$eva'. Must be a 6-8 digit integer.";
      }
    }
    
    // Validate timestamp format
    if (connectionData.containsKey('ts')) {
      final ts = connectionData['ts'] as String?;
      if (ts == null || ts.length != 10 || !RegExp(r'^\d{10}$').hasMatch(ts)) {
        errors['ts'] = 
            "Invalid timestamp format '$ts'. Expected 10-digit string in YYMMddHHmm format.";
      }
    }
    
    return errors.isEmpty
        ? ConnectionValidationResult.valid()
        : ConnectionValidationResult.invalid(errors);
  }
}