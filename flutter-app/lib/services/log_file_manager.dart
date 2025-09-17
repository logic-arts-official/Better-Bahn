/// Cross-platform log file management service for Better-Bahn
/// 
/// Handles persistent log storage and cross-platform file sharing
/// - Windows: Creates .txt files for Notepad++ compatibility
/// - Android: Saves to Downloads directory with sharing support
/// - Web: Triggers browser download of log file

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:share_plus/share_plus.dart';

// Platform-specific imports
import 'dart:io';
import 'package:path_provider/path_provider.dart';

// Web support
import 'dart:html' as html show document, AnchorElement;

class LogFileManager {
  static const String _logFileName = 'better_bahn_logs.txt';
  static const int _maxLogEntries = 1000;
  
  /// Get the appropriate log file path for the current platform
  static Future<String> _getLogFilePath() async {
    if (kIsWeb) {
      // Web doesn't need a persistent file path
      return _logFileName;
    }
    
    try {
      Directory directory;
      
      if (Platform.isAndroid) {
        // Use external storage directory for Android
        directory = await getExternalStorageDirectory() ?? 
                   await getApplicationDocumentsDirectory();
      } else if (Platform.isWindows) {
        // Use Documents directory for Windows
        directory = await getApplicationDocumentsDirectory();
      } else {
        // Default to application documents directory
        directory = await getApplicationDocumentsDirectory();
      }
      
      return '${directory.path}/$_logFileName';
    } catch (e) {
      // Fallback to temporary directory
      final tempDir = await getTemporaryDirectory();
      return '${tempDir.path}/$_logFileName';
    }
  }
  
  /// Save log messages to persistent storage
  static Future<void> saveLogMessages(List<String> logMessages) async {
    try {
      final logContent = _formatLogContent(logMessages);
      
      if (kIsWeb) {
        // Web: We'll handle this differently in the export method
        return;
      }
      
      final filePath = await _getLogFilePath();
      final file = File(filePath);
      
      // Ensure parent directory exists
      await file.parent.create(recursive: true);
      
      // Write log content with UTF-8 encoding
      await file.writeAsString(logContent, encoding: utf8);
      
      debugPrint('Log file saved: $filePath');
    } catch (e) {
      debugPrint('Error saving log file: $e');
    }
  }
  
  /// Export log file for sharing/opening with default app
  static Future<bool> exportLogFile(List<String> logMessages) async {
    try {
      final logContent = _formatLogContent(logMessages);
      
      if (kIsWeb) {
        return _downloadWebFile(logContent);
      }
      
      // Save the current logs first
      await saveLogMessages(logMessages);
      final filePath = await _getLogFilePath();
      
      if (Platform.isAndroid || Platform.isIOS) {
        // Mobile: Use share functionality
        await Share.shareXFiles(
          [XFile(filePath)],
          text: 'Better-Bahn Log File',
          subject: 'Better-Bahn Logs - ${DateTime.now().toIso8601String().split('T')[0]}',
        );
      } else {
        // Desktop: Try to open with default application
        await _openWithDefaultApp(filePath);
      }
      
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
      final timestamp = DateTime.now().subtract(Duration(seconds: entries.length - i));
      buffer.writeln('[${timestamp.toIso8601String()}] ${entries[i]}');
    }
    
    buffer.writeln();
    buffer.writeln('${'-' * 50}');
    buffer.writeln('End of log file');
    
    return buffer.toString();
  }
  
  /// Get platform-specific name for log header
  static String _getPlatformName() {
    if (kIsWeb) return 'Web';
    if (Platform.isAndroid) return 'Android';
    if (Platform.isIOS) return 'iOS';
    if (Platform.isWindows) return 'Windows';
    if (Platform.isMacOS) return 'macOS';
    if (Platform.isLinux) return 'Linux';
    return 'Unknown';
  }
  
  /// Download file in web browser
  static Future<bool> _downloadWebFile(String content) async {
    if (!kIsWeb) return false;
    
    try {
      // For web platforms, create a downloadable data URL
      final bytes = utf8.encode(content);
      final dataUrl = 'data:text/plain;charset=utf-8;base64,${base64.encode(bytes)}';
      
      // Use the browser's download mechanism
      final anchor = document.createElement('a') as AnchorElement;
      anchor.href = dataUrl;
      anchor.download = _logFileName;
      anchor.style.display = 'none';
      
      document.body?.append(anchor);
      anchor.click();
      anchor.remove();
      
      return true;
    } catch (e) {
      debugPrint('Error downloading web file: $e');
      return false;
    }
  }
  
  /// Open file with default system application
  static Future<void> _openWithDefaultApp(String filePath) async {
    try {
      if (Platform.isWindows) {
        await Process.run('cmd', ['/c', 'start', '', filePath]);
      } else if (Platform.isMacOS) {
        await Process.run('open', [filePath]);
      } else if (Platform.isLinux) {
        await Process.run('xdg-open', [filePath]);
      }
    } catch (e) {
      debugPrint('Could not open file with default app: $e');
      // Fallback: just show the file path to user
      rethrow;
    }
  }
  
  /// Get the current log file path (for display purposes)
  static Future<String?> getCurrentLogFilePath() async {
    if (kIsWeb) return null;
    
    try {
      return await _getLogFilePath();
    } catch (e) {
      return null;
    }
  }
  
  /// Check if log file exists
  static Future<bool> logFileExists() async {
    if (kIsWeb) return false;
    
    try {
      final filePath = await _getLogFilePath();
      return File(filePath).exists();
    } catch (e) {
      return false;
    }
  }
  
  /// Get log file size in bytes
  static Future<int> getLogFileSize() async {
    if (kIsWeb) return 0;
    
    try {
      final filePath = await _getLogFilePath();
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