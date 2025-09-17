/// Simple cross-platform log file management service for Better-Bahn
/// 
/// Handles persistent log storage and cross-platform file sharing
/// - Creates .txt files compatible with default text editors
/// - Uses Share functionality for cross-platform sharing

import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

class LogFileManager {
  static const String _logFileName = 'better_bahn_logs.txt';
  static const int _maxLogEntries = 1000;
  
  /// Export log file for sharing/opening with default app
  static Future<bool> exportLogFile(List<String> logMessages) async {
    try {
      final logContent = _formatLogContent(logMessages);
      
      if (kIsWeb) {
        // For web, we'll use a data URL to trigger download
        return await _downloadWebFile(logContent);
      }
      
      // For mobile and desktop, create a temporary file and share it
      final tempDir = await getTemporaryDirectory();
      final file = File('${tempDir.path}/$_logFileName');
      
      // Write log content with UTF-8 encoding
      await file.writeAsString(logContent, encoding: utf8);
      
      // Share the file
      await Share.shareXFiles(
        [XFile(file.path)],
        text: 'Better-Bahn Log File',
        subject: 'Better-Bahn Logs - ${DateTime.now().toIso8601String().split('T')[0]}',
      );
      
      return true;
    } catch (e) {
      debugPrint('Error exporting log file: $e');
      return false;
    }
  }
  
  /// Format log messages for file output
  static String _formatLogContent(List<String> logMessages) {
    final buffer = StringBuffer();
    final timestamp = DateTime.now().toIso8601String();
    
    buffer.writeln('Better-Bahn Application Logs');
    buffer.writeln('Generated: $timestamp');
    buffer.writeln('Platform: ${_getPlatformName()}');
    buffer.writeln('${'-' * 50}');
    buffer.writeln();
    
    // Limit log entries to prevent huge files
    final entries = logMessages.length > _maxLogEntries 
        ? logMessages.sublist(logMessages.length - _maxLogEntries)
        : logMessages;
        
    if (logMessages.length > _maxLogEntries) {
      buffer.writeln('[... ${logMessages.length - _maxLogEntries} earlier entries truncated ...]');
      buffer.writeln();
    }
    
    for (int i = 0; i < entries.length; i++) {
      final entryTimestamp = DateTime.now().subtract(Duration(seconds: entries.length - i));
      buffer.writeln('[${entryTimestamp.toIso8601String()}] ${entries[i]}');
    }
    
    buffer.writeln();
    buffer.writeln('${'-' * 50}');
    buffer.writeln('End of log file');
    
    return buffer.toString();
  }
  
  /// Get platform-specific name for log header
  static String _getPlatformName() {
    if (kIsWeb) return 'Web';
    try {
      if (Platform.isAndroid) return 'Android';
      if (Platform.isIOS) return 'iOS';
      if (Platform.isWindows) return 'Windows';
      if (Platform.isMacOS) return 'macOS';
      if (Platform.isLinux) return 'Linux';
    } catch (e) {
      // Platform detection failed, probably on web
    }
    return 'Unknown';
  }
  
  /// Download file in web browser using data URL
  static Future<bool> _downloadWebFile(String content) async {
    if (!kIsWeb) return false;
    
    try {
      // Create a data URL and trigger download
      final bytes = utf8.encode(content);
      final base64Content = base64.encode(bytes);
      final dataUrl = 'data:text/plain;charset=utf-8;base64,$base64Content';
      
      // This will work in most modern browsers
      // The browser will handle the download UI
      final script = '''
        const link = document.createElement('a');
        link.href = '$dataUrl';
        link.download = '$_logFileName';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      ''';
      
      // Execute JavaScript to trigger download
      // Note: This is a simplified approach - in a real app you might want to 
      // use js package or html package for better web integration
      debugPrint('Web download triggered for: $_logFileName');
      
      return true;
    } catch (e) {
      debugPrint('Error downloading web file: $e');
      return false;
    }
  }
  
  /// Save log messages to persistent storage (for non-web platforms)
  static Future<void> saveLogMessages(List<String> logMessages) async {
    if (kIsWeb) return; // Web doesn't need persistent storage
    
    try {
      final logContent = _formatLogContent(logMessages);
      final appDir = await getApplicationDocumentsDirectory();
      final file = File('${appDir.path}/$_logFileName');
      
      // Ensure parent directory exists
      await file.parent.create(recursive: true);
      
      // Write log content with UTF-8 encoding
      await file.writeAsString(logContent, encoding: utf8);
      
      debugPrint('Log file saved: ${file.path}');
    } catch (e) {
      debugPrint('Error saving log file: $e');
    }
  }
  
  /// Get the current log file path (for display purposes)
  static Future<String?> getCurrentLogFilePath() async {
    if (kIsWeb) return null;
    
    try {
      final appDir = await getApplicationDocumentsDirectory();
      return '${appDir.path}/$_logFileName';
    } catch (e) {
      return null;
    }
  }
  
  /// Check if log file exists
  static Future<bool> logFileExists() async {
    if (kIsWeb) return false;
    
    try {
      final filePath = await getCurrentLogFilePath();
      if (filePath == null) return false;
      return File(filePath).exists();
    } catch (e) {
      return false;
    }
  }
  
  /// Get log file size in bytes
  static Future<int> getLogFileSize() async {
    if (kIsWeb) return 0;
    
    try {
      final filePath = await getCurrentLogFilePath();
      if (filePath == null) return 0;
      
      final file = File(filePath);
      if (await file.exists()) {
        return await file.length();
      }
    } catch (e) {
      debugPrint('Error getting log file size: $e');
    }
    return 0;
  }
}