import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/logging_service.dart';

/// State management service that clearly separates app state from process state
/// Follows 12-Factor principle of stateless processes with explicit state handling
class AppStateService extends ChangeNotifier {
  // Analysis state
  bool _isAnalyzing = false;
  String _resultText = '';
  List<String> _logMessages = [];
  bool _hasResult = false;
  
  // Progress tracking
  int _totalStations = 0;
  int _processedStations = 0;
  double _progress = 0.0;
  
  // Results
  double _directPrice = 0;
  double _splitPrice = 0;
  List<SplitTicket> _splitTickets = [];
  
  // UI state
  bool _showLogs = false;
  
  // Stream controllers for reactive updates (properly disposed)
  final StreamController<AnalysisProgress> _progressController = StreamController<AnalysisProgress>.broadcast();
  final StreamController<String> _logController = StreamController<String>.broadcast();
  
  // Getters for state access
  bool get isAnalyzing => _isAnalyzing;
  String get resultText => _resultText;
  List<String> get logMessages => List.unmodifiable(_logMessages);
  bool get hasResult => _hasResult;
  int get totalStations => _totalStations;
  int get processedStations => _processedStations;
  double get progress => _progress;
  double get directPrice => _directPrice;
  double get splitPrice => _splitPrice;
  List<SplitTicket> get splitTickets => List.unmodifiable(_splitTickets);
  bool get showLogs => _showLogs;
  
  // Stream getters
  Stream<AnalysisProgress> get progressStream => _progressController.stream;
  Stream<String> get logStream => _logController.stream;
  
  /// Start analysis process
  void startAnalysis() {
    LoggingService.logFeatureUsage('split_ticket_analysis');
    
    _isAnalyzing = true;
    _resultText = 'Analysiere Verbindung...';
    _hasResult = false;
    _splitTickets = [];
    _logMessages = [];
    _progress = 0.0;
    _totalStations = 0;
    _processedStations = 0;
    notifyListeners();
    
    LoggingService.info('Analysis started');
  }
  
  /// Update analysis progress
  void updateProgress(int processed, int total) {
    _processedStations = processed;
    _totalStations = total;
    _progress = total > 0 ? processed / total : 0.0;
    
    final progressData = AnalysisProgress(
      processed: processed,
      total: total,
      progress: _progress,
    );
    
    _progressController.add(progressData);
    notifyListeners();
    
    LoggingService.debug(
      'Progress updated',
      metadata: {
        'processed': processed,
        'total': total,
        'progress': (_progress * 100).toInt(),
      },
    );
  }
  
  /// Add log message with size limiting
  void addLogMessage(String message) {
    _logMessages.add(message);
    
    // Limit log messages to prevent memory issues
    if (_logMessages.length > 100) {
      _logMessages.removeAt(0);
    }
    
    _logController.add(message);
    notifyListeners();
    
    // Use structured logging
    LoggingService.debug(message, tag: 'AnalysisLog');
  }
  
  /// Complete analysis with results
  void completeAnalysis({
    required double directPrice,
    required double splitPrice,
    required List<SplitTicket> splitTickets,
  }) {
    _isAnalyzing = false;
    _hasResult = true;
    _directPrice = directPrice;
    _splitPrice = splitPrice;
    _splitTickets = List.from(splitTickets);
    
    if (_splitPrice < _directPrice) {
      _resultText = 'Günstigere Split-Ticket-Option gefunden!';
      LoggingService.info(
        'Analysis completed: cheaper option found',
        metadata: {
          'directPrice': directPrice,
          'splitPrice': splitPrice,
          'savings': directPrice - splitPrice,
          'ticketCount': splitTickets.length,
        },
      );
    } else {
      _resultText = 'Keine günstigere Split-Option gefunden.';
      LoggingService.info(
        'Analysis completed: no cheaper option found',
        metadata: {
          'directPrice': directPrice,
          'splitPrice': splitPrice,
        },
      );
    }
    
    notifyListeners();
  }
  
  /// Complete analysis with error
  void completeAnalysisWithError(String error) {
    _isAnalyzing = false;
    _resultText = 'Fehler: $error';
    _hasResult = false;
    notifyListeners();
    
    LoggingService.error(
      'Analysis completed with error',
      metadata: {'error': error},
    );
  }
  
  /// Toggle log visibility
  void toggleLogVisibility() {
    _showLogs = !_showLogs;
    notifyListeners();
    
    LoggingService.logFeatureUsage(
      'toggle_logs',
      metadata: {'visible': _showLogs},
    );
  }
  
  /// Clear analysis state
  void clearAnalysis() {
    _isAnalyzing = false;
    _resultText = '';
    _logMessages = [];
    _hasResult = false;
    _totalStations = 0;
    _processedStations = 0;
    _progress = 0.0;
    _directPrice = 0;
    _splitPrice = 0;
    _splitTickets = [];
    _showLogs = false;
    notifyListeners();
    
    LoggingService.info('Analysis state cleared');
  }
  
  /// Get app state summary for debugging
  Map<String, dynamic> getStateSummary() {
    return {
      'isAnalyzing': _isAnalyzing,
      'hasResult': _hasResult,
      'progress': _progress,
      'totalStations': _totalStations,
      'processedStations': _processedStations,
      'directPrice': _directPrice,
      'splitPrice': _splitPrice,
      'ticketCount': _splitTickets.length,
      'logMessageCount': _logMessages.length,
      'showLogs': _showLogs,
    };
  }
  
  @override
  void dispose() {
    // Clean disposal of streams/controllers - Factor 9 (Disposability)
    LoggingService.info('Disposing AppStateService');
    
    _progressController.close();
    _logController.close();
    
    super.dispose();
  }
}

/// Data class for analysis progress updates
class AnalysisProgress {
  final int processed;
  final int total;
  final double progress;
  
  const AnalysisProgress({
    required this.processed,
    required this.total,
    required this.progress,
  });
  
  @override
  String toString() => 'AnalysisProgress(processed: $processed, total: $total, progress: $progress)';
}

/// Data class for split ticket information
class SplitTicket {
  final String from;
  final String to;
  final double price;
  final String fromId;
  final String toId;
  final String departureIso;
  final bool coveredByDeutschlandTicket;

  const SplitTicket({
    required this.from,
    required this.to,
    required this.price,
    required this.fromId,
    required this.toId,
    required this.departureIso,
    this.coveredByDeutschlandTicket = false,
  });
  
  @override
  String toString() => 'SplitTicket(from: $from, to: $to, price: $price)';
}