import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import 'logging_service.dart';

/// Abstract interface for Deutsche Bahn API services
/// Provides exchangeable backing service implementation following 12-Factor principles
abstract class BahnApiService {
  Future<Map<String, dynamic>> resolveVbidToConnection(
    String vbid,
    List<Map<String, dynamic>> travellerPayload,
    bool hasDeutschlandTicket,
  );
  
  Future<Map<String, dynamic>> getConnectionDetails(
    String fromStationId,
    String toStationId,
    String date,
    String departureTime,
    List<Map<String, dynamic>> travellerPayload,
    bool hasDeutschlandTicket,
  );
}

/// HTTP-based implementation of Deutsche Bahn API service
/// Encapsulates all external API calls as exchangeable clients
class HttpBahnApiService implements BahnApiService {
  final http.Client _httpClient;
  final String _baseUrl;
  final int _timeoutMs;
  final String _userAgent;
  
  HttpBahnApiService({
    http.Client? httpClient,
    String? baseUrl,
    int? timeoutMs,
    String? userAgent,
  }) : _httpClient = httpClient ?? http.Client(),
       _baseUrl = baseUrl ?? AppConfig.bahnApiBaseUrl,
       _timeoutMs = timeoutMs ?? AppConfig.defaultRequestTimeout,
       _userAgent = userAgent ?? AppConfig.userAgent;

  Map<String, String> get _defaultHeaders => {
    'User-Agent': _userAgent,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
  };

  Future<Map<String, dynamic>> _makeRequest({
    required String method,
    required String endpoint,
    Map<String, dynamic>? body,
    Map<String, String>? additionalHeaders,
  }) async {
    final url = '$_baseUrl$endpoint';
    final headers = {..._defaultHeaders, ...?additionalHeaders};
    
    final stopwatch = Stopwatch()..start();
    
    try {
      LoggingService.logNetworkRequest(
        method: method,
        url: url,
        headers: headers,
        body: body != null ? json.encode(body) : null,
      );
      
      late http.Response response;
      
      if (method == 'GET') {
        response = await _httpClient.get(
          Uri.parse(url),
          headers: headers,
        ).timeout(Duration(milliseconds: _timeoutMs));
      } else if (method == 'POST') {
        response = await _httpClient.post(
          Uri.parse(url),
          headers: headers,
          body: body != null ? json.encode(body) : null,
        ).timeout(Duration(milliseconds: _timeoutMs));
      } else {
        throw ArgumentError('Unsupported HTTP method: $method');
      }
      
      stopwatch.stop();
      
      LoggingService.logNetworkRequest(
        method: method,
        url: url,
        statusCode: response.statusCode,
        responseTime: '${stopwatch.elapsedMilliseconds}ms',
      );
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        if (response.body.isNotEmpty) {
          return json.decode(response.body) as Map<String, dynamic>;
        } else {
          // Handle 201 responses with empty body - may need retry
          if (response.statusCode == 201) {
            LoggingService.warning(
              'Received 201 with empty body, may need retry',
              metadata: {'endpoint': endpoint},
            );
          }
          return {};
        }
      } else {
        LoggingService.error(
          'HTTP request failed',
          metadata: {
            'statusCode': response.statusCode,
            'endpoint': endpoint,
            'responseBody': response.body.isNotEmpty ? response.body : null,
          },
        );
        throw BahnApiException(
          'HTTP ${response.statusCode}: ${response.reasonPhrase}',
          statusCode: response.statusCode,
        );
      }
    } on TimeoutException {
      stopwatch.stop();
      LoggingService.error(
        'Request timeout',
        metadata: {
          'endpoint': endpoint,
          'timeoutMs': _timeoutMs,
          'elapsedMs': stopwatch.elapsedMilliseconds,
        },
      );
      throw BahnApiException('Request timeout after ${_timeoutMs}ms');
    } catch (e) {
      stopwatch.stop();
      LoggingService.error(
        'Network request failed',
        error: e,
        metadata: {
          'endpoint': endpoint,
          'elapsedMs': stopwatch.elapsedMilliseconds,
        },
      );
      rethrow;
    }
  }

  @override
  Future<Map<String, dynamic>> resolveVbidToConnection(
    String vbid,
    List<Map<String, dynamic>> travellerPayload,
    bool hasDeutschlandTicket,
  ) async {
    LoggingService.info('Resolving VBID to connection', metadata: {'vbid': vbid});
    
    try {
      // Step 1: Get the 'recon' string from the vbid endpoint
      final vbidData = await _makeRequest(
        method: 'GET',
        endpoint: '/angebote/verbindung/$vbid',
      );
      
      final reconString = vbidData['hinfahrtRecon'];
      if (reconString == null) {
        throw BahnApiException('Could not extract hinfahrtRecon from VBID response');
      }
      
      LoggingService.debug('Successfully extracted recon string from VBID');
      
      // Step 2: Use the 'recon' string to get the full connection data
      final payload = {
        'klasse': 'KLASSE_2',
        'reisende': travellerPayload,
        'ctxRecon': reconString,
        'deutschlandTicketVorhanden': hasDeutschlandTicket,
      };
      
      final connectionData = await _makeRequest(
        method: 'POST',
        endpoint: '/angebote/recon',
        body: payload,
      );
      
      // Handle potential 201 response with retry logic
      if (connectionData.isEmpty) {
        LoggingService.warning('Empty response from recon endpoint, retrying...');
        await Future.delayed(const Duration(milliseconds: 1000));
        
        return await _makeRequest(
          method: 'POST',
          endpoint: '/angebote/recon',
          body: payload,
        );
      }
      
      LoggingService.info('Successfully resolved VBID to connection data');
      return connectionData;
      
    } catch (e) {
      LoggingService.error(
        'Failed to resolve VBID to connection',
        error: e,
        metadata: {'vbid': vbid},
      );
      rethrow;
    }
  }

  @override
  Future<Map<String, dynamic>> getConnectionDetails(
    String fromStationId,
    String toStationId,
    String date,
    String departureTime,
    List<Map<String, dynamic>> travellerPayload,
    bool hasDeutschlandTicket,
  ) async {
    LoggingService.info(
      'Getting connection details',
      metadata: {
        'from': fromStationId,
        'to': toStationId,
        'date': date,
        'time': departureTime,
      },
    );
    
    try {
      final payload = {
        'abfahrtsHalt': fromStationId,
        'anfrageZeitpunkt': '${date}T$departureTime',
        'ankunftsHalt': toStationId,
        'ankunftSuche': 'ABFAHRT',
        'klasse': 'KLASSE_2',
        'produktgattungen': [
          'ICE',
          'EC_IC',
          'IR',
          'REGIONAL',
          'SBAHN',
          'BUS',
          'SCHIFF',
          'UBAHN',
          'TRAM',
          'ANRUFPFLICHTIG',
        ],
        'reisende': travellerPayload,
        'schnelleVerbindungen': true,
        'deutschlandTicketVorhanden': hasDeutschlandTicket,
      };
      
      final connectionData = await _makeRequest(
        method: 'POST',
        endpoint: '/angebote/fahrplan',
        body: payload,
      );
      
      // Handle potential 201 response with retry logic
      if (connectionData.isEmpty) {
        LoggingService.warning('Empty response from fahrplan endpoint, retrying...');
        await Future.delayed(const Duration(milliseconds: 1000));
        
        return await _makeRequest(
          method: 'POST',
          endpoint: '/angebote/fahrplan',
          body: payload,
        );
      }
      
      LoggingService.info('Successfully retrieved connection details');
      return connectionData;
      
    } catch (e) {
      LoggingService.error(
        'Failed to get connection details',
        error: e,
        metadata: {
          'from': fromStationId,
          'to': toStationId,
          'date': date,
          'time': departureTime,
        },
      );
      rethrow;
    }
  }
  
  void dispose() {
    _httpClient.close();
  }
}

/// Custom exception for Bahn API errors
class BahnApiException implements Exception {
  final String message;
  final int? statusCode;
  
  const BahnApiException(this.message, {this.statusCode});
  
  @override
  String toString() => 'BahnApiException: $message';
}