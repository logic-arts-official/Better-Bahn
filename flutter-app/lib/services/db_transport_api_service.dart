/// v6.db.transport.rest API Service for Better-Bahn Flutter App
/// 
/// This service provides access to real-time Deutsche Bahn data through
/// the v6.db.transport.rest API, complementing the existing bahn.de web API
/// with additional real-time features like live delays and journey updates.
/// 
/// API Documentation: https://v6.db.transport.rest/api.html

import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;

/// Real-time status information for a journey
class RealTimeStatus {
  final bool hasDelays;
  final int totalDelayMinutes;
  final int cancelledLegs;

  RealTimeStatus({
    required this.hasDelays,
    required this.totalDelayMinutes,
    required this.cancelledLegs,
  });

  factory RealTimeStatus.fromJson(Map<String, dynamic> json) {
    return RealTimeStatus(
      hasDelays: json['has_delays'] ?? false,
      totalDelayMinutes: json['total_delay_minutes'] ?? 0,
      cancelledLegs: json['cancelled_legs'] ?? 0,
    );
  }
}

/// Information about a real-time journey
class RealTimeJourneyInfo {
  final bool available;
  final int journeysCount;
  final List<JourneyInfo> journeys;

  RealTimeJourneyInfo({
    required this.available,
    required this.journeysCount,
    required this.journeys,
  });
}

/// Information about a single journey option
class JourneyInfo {
  final int durationMinutes;
  final int transfers;
  final RealTimeStatus realTimeStatus;

  JourneyInfo({
    required this.durationMinutes,
    required this.transfers,
    required this.realTimeStatus,
  });
}

/// Location result from the API
class Location {
  final String id;
  final String name;
  final String type;
  final double? latitude;
  final double? longitude;

  Location({
    required this.id,
    required this.name,
    required this.type,
    this.latitude,
    this.longitude,
  });

  factory Location.fromJson(Map<String, dynamic> json) {
    final location = json['location'] as Map<String, dynamic>?;
    return Location(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      type: json['type'] ?? '',
      latitude: location?['latitude']?.toDouble(),
      longitude: location?['longitude']?.toDouble(),
    );
  }
}

/// Exception thrown when the API request fails
class DBTransportAPIException implements Exception {
  final String message;
  final int? statusCode;

  DBTransportAPIException(this.message, [this.statusCode]);

  @override
  String toString() => 'DBTransportAPIException: $message';
}

/// Service class for interacting with the v6.db.transport.rest API
class DBTransportAPIService {
  static const String baseUrl = 'https://v6.db.transport.rest';
  
  final http.Client client;
  final Duration rateLimitDelay;

  DBTransportAPIService({
    http.Client? client,
    this.rateLimitDelay = const Duration(milliseconds: 200),
  }) : client = client ?? http.Client();

  /// Make an API request with rate limiting and error handling
  Future<Map<String, dynamic>?> _makeRequest(
    String endpoint, {
    Map<String, String>? params,
  }) async {
    await Future.delayed(rateLimitDelay);

    try {
      final uri = Uri.parse('$baseUrl$endpoint').replace(queryParameters: params);
      final response = await client.get(
        uri,
        headers: {
          'User-Agent': 'Better-Bahn/1.0 (Flutter App)',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        throw DBTransportAPIException(
          'API request failed: ${response.statusCode} - ${response.body}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is DBTransportAPIException) rethrow;
      throw DBTransportAPIException('Network error: $e');
    }
  }

  /// Find stations by name or location
  Future<List<Location>> findLocations(String query, {int results = 5}) async {
    try {
      final response = await _makeRequest('/locations', params: {
        'query': query,
        'results': results.toString(),
      });

      if (response == null) return [];

      if (response is List) {
        return response.map((item) => Location.fromJson(item)).toList();
      } else if (response.containsKey('locations')) {
        final locations = response['locations'] as List<dynamic>;
        return locations.map((item) => Location.fromJson(item)).toList();
      }

      return [];
    } catch (e) {
      print('Error finding locations: $e');
      return [];
    }
  }

  /// Get journey options between two stations
  Future<Map<String, dynamic>?> getJourneys({
    required String fromStation,
    required String toStation,
    String? departure,
    int results = 3,
    bool stopovers = true,
  }) async {
    try {
      final params = <String, String>{
        'from': fromStation,
        'to': toStation,
        'results': results.toString(),
        'stopovers': stopovers.toString(),
      };

      if (departure != null) params['departure'] = departure;

      return await _makeRequest('/journeys', params: params);
    } catch (e) {
      print('Error getting journeys: $e');
      return null;
    }
  }

  /// Get real-time journey information
  Future<RealTimeJourneyInfo?> getRealTimeJourneyInfo({
    required String fromStationName,
    required String toStationName,
    String? departureTime,
  }) async {
    try {
      // Find stations
      final fromLocations = await findLocations(fromStationName, results: 1);
      final toLocations = await findLocations(toStationName, results: 1);

      if (fromLocations.isEmpty || toLocations.isEmpty) {
        return null;
      }

      final fromId = fromLocations[0].id;
      final toId = toLocations[0].id;

      // Get journey data
      final journeyData = await getJourneys(
        fromStation: fromId,
        toStation: toId,
        departure: departureTime,
        results: 3,
        stopovers: true,
      );

      if (journeyData == null || !journeyData.containsKey('journeys')) {
        return null;
      }

      final journeys = journeyData['journeys'] as List<dynamic>;
      final journeyInfoList = <JourneyInfo>[];

      // Process first 2 journeys
      for (int i = 0; i < journeys.length && i < 2; i++) {
        final journey = journeys[i] as Map<String, dynamic>;
        final status = _getRealTimeStatus(journey);
        
        final journeyInfo = JourneyInfo(
          durationMinutes: journey['duration'] != null 
              ? (journey['duration'] as int) ~/ 60000 
              : 0,
          transfers: (journey['legs'] as List?)?.length ?? 0 - 1,
          realTimeStatus: status,
        );
        
        journeyInfoList.add(journeyInfo);
      }

      return RealTimeJourneyInfo(
        available: true,
        journeysCount: journeys.length,
        journeys: journeyInfoList,
      );
    } catch (e) {
      print('Error getting real-time journey info: $e');
      return null;
    }
  }

  /// Extract real-time status from journey data
  RealTimeStatus _getRealTimeStatus(Map<String, dynamic> journeyData) {
    bool hasDelays = false;
    int totalDelayMinutes = 0;
    int cancelledLegs = 0;

    final legs = journeyData['legs'] as List<dynamic>? ?? [];

    for (final leg in legs) {
      final legMap = leg as Map<String, dynamic>;

      // Check departure delay
      final departure = legMap['departure'] as Map<String, dynamic>?;
      if (departure != null && departure['delay'] != null) {
        final delaySeconds = departure['delay'] as int;
        totalDelayMinutes += delaySeconds ~/ 60;
        hasDelays = true;
      }

      // Check arrival delay
      final arrival = legMap['arrival'] as Map<String, dynamic>?;
      if (arrival != null && arrival['delay'] != null) {
        final delaySeconds = arrival['delay'] as int;
        totalDelayMinutes += delaySeconds ~/ 60;
        hasDelays = true;
      }

      // Check cancellation
      if (legMap['cancelled'] == true) {
        cancelledLegs++;
      }
    }

    return RealTimeStatus(
      hasDelays: hasDelays,
      totalDelayMinutes: totalDelayMinutes,
      cancelledLegs: cancelledLegs,
    );
  }

  /// Dispose of resources
  void dispose() {
    client.close();
  }
}
