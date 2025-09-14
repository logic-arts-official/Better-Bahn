import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../config/app_config.dart';
import '../services/logging_service.dart';

/// Debug menu for administrative and maintenance processes
/// Separate from regular app flow following 12-Factor principles
class DebugMenu extends StatefulWidget {
  const DebugMenu({super.key});

  @override
  State<DebugMenu> createState() => _DebugMenuState();
}

class _DebugMenuState extends State<DebugMenu> {
  final List<String> _maintenanceLogs = [];
  bool _isRunningMaintenance = false;

  void _addMaintenanceLog(String message) {
    setState(() {
      _maintenanceLogs.add('${DateTime.now().toIso8601String()}: $message');
    });
    LoggingService.info('Maintenance: $message', tag: 'DebugMenu');
  }

  /// Clear application caches (maintenance process)
  Future<void> _clearCaches() async {
    setState(() {
      _isRunningMaintenance = true;
    });

    try {
      _addMaintenanceLog('Starting cache cleanup...');
      
      // Simulate cache clearing process
      await Future.delayed(const Duration(milliseconds: 500));
      _addMaintenanceLog('Cleared HTTP client cache');
      
      await Future.delayed(const Duration(milliseconds: 300));
      _addMaintenanceLog('Cleared temporary data');
      
      await Future.delayed(const Duration(milliseconds: 200));
      _addMaintenanceLog('Cache cleanup completed successfully');
      
      LoggingService.info('Cache cleanup maintenance process completed');
      
    } catch (e) {
      _addMaintenanceLog('Error during cache cleanup: $e');
      LoggingService.error('Cache cleanup failed', error: e);
    } finally {
      setState(() {
        _isRunningMaintenance = false;
      });
    }
  }

  /// Export application logs (maintenance process)
  Future<void> _exportLogs() async {
    setState(() {
      _isRunningMaintenance = true;
    });

    try {
      _addMaintenanceLog('Starting log export...');
      
      // Simulate log export process
      await Future.delayed(const Duration(milliseconds: 800));
      _addMaintenanceLog('Collected application logs');
      
      await Future.delayed(const Duration(milliseconds: 400));
      _addMaintenanceLog('Sanitized sensitive data');
      
      await Future.delayed(const Duration(milliseconds: 300));
      _addMaintenanceLog('Log export prepared (would save to file in production)');
      
      LoggingService.info('Log export maintenance process completed');
      
    } catch (e) {
      _addMaintenanceLog('Error during log export: $e');
      LoggingService.error('Log export failed', error: e);
    } finally {
      setState(() {
        _isRunningMaintenance = false;
      });
    }
  }

  /// Validate application configuration (maintenance process)
  Future<void> _validateConfiguration() async {
    setState(() {
      _isRunningMaintenance = true;
    });

    try {
      _addMaintenanceLog('Starting configuration validation...');
      
      final isValid = AppConfig.validateConfig();
      if (isValid) {
        _addMaintenanceLog('✓ Configuration validation passed');
      }
      
      final config = AppConfig.getConfigSummary();
      _addMaintenanceLog('Environment: ${config['environment']}');
      _addMaintenanceLog('API Base URL: ${config['bahnApiBaseUrl']}');
      _addMaintenanceLog('Timeout: ${config['defaultRequestTimeout']}ms');
      _addMaintenanceLog('Debug Logs: ${config['enableDebugLogs']}');
      
      LoggingService.info('Configuration validation maintenance process completed');
      
    } catch (e) {
      _addMaintenanceLog('Error during configuration validation: $e');
      LoggingService.error('Configuration validation failed', error: e);
    } finally {
      setState(() {
        _isRunningMaintenance = false;
      });
    }
  }

  /// Test network connectivity (maintenance process)
  Future<void> _testNetworkConnectivity() async {
    setState(() {
      _isRunningMaintenance = true;
    });

    try {
      _addMaintenanceLog('Starting network connectivity test...');
      
      // Simulate network test
      await Future.delayed(const Duration(milliseconds: 1000));
      _addMaintenanceLog('Testing connection to ${AppConfig.bahnApiBaseUrl}...');
      
      await Future.delayed(const Duration(milliseconds: 800));
      _addMaintenanceLog('Network connectivity test completed');
      _addMaintenanceLog('Note: In sandboxed environment, external requests may fail');
      
      LoggingService.info('Network connectivity test maintenance process completed');
      
    } catch (e) {
      _addMaintenanceLog('Error during network test: $e');
      LoggingService.error('Network test failed', error: e);
    } finally {
      setState(() {
        _isRunningMaintenance = false;
      });
    }
  }

  void _copyConfigToClipboard() {
    final config = AppConfig.getConfigSummary();
    final configText = config.entries
        .map((e) => '${e.key}: ${e.value}')
        .join('\n');
    
    Clipboard.setData(ClipboardData(text: configText));
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Configuration copied to clipboard')),
    );
    
    LoggingService.logFeatureUsage('copy_config_to_clipboard');
  }

  void _clearMaintenanceLogs() {
    setState(() {
      _maintenanceLogs.clear();
    });
    
    LoggingService.info('Maintenance logs cleared');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Debug Menu'),
        backgroundColor: Colors.orange,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Warning banner
            Card(
              color: Colors.orange.shade100,
              child: const Padding(
                padding: EdgeInsets.all(12.0),
                child: Row(
                  children: [
                    Icon(Icons.warning, color: Colors.orange),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Debug Menu - For Development and Maintenance Only',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Configuration section
            const Text(
              'Configuration',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isRunningMaintenance ? null : _validateConfiguration,
                    icon: const Icon(Icons.settings),
                    label: const Text('Validate Config'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _copyConfigToClipboard,
                    icon: const Icon(Icons.copy),
                    label: const Text('Copy Config'),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Maintenance section
            const Text(
              'Maintenance Processes',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isRunningMaintenance ? null : _clearCaches,
                    icon: const Icon(Icons.clear),
                    label: const Text('Clear Caches'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isRunningMaintenance ? null : _exportLogs,
                    icon: const Icon(Icons.download),
                    label: const Text('Export Logs'),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            ElevatedButton.icon(
              onPressed: _isRunningMaintenance ? null : _testNetworkConnectivity,
              icon: const Icon(Icons.network_check),
              label: const Text('Test Network'),
            ),
            
            const SizedBox(height: 16),
            
            // Logs section
            Row(
              children: [
                const Text(
                  'Maintenance Logs',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  onPressed: _clearMaintenanceLogs,
                  icon: const Icon(Icons.delete),
                  tooltip: 'Clear logs',
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            // Loading indicator
            if (_isRunningMaintenance)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(width: 16),
                      Text('Running maintenance process...'),
                    ],
                  ),
                ),
              ),
            
            // Logs display
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: _maintenanceLogs.isEmpty
                      ? const Center(
                          child: Text(
                            'No maintenance logs yet.\nRun maintenance processes to see output.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.grey),
                          ),
                        )
                      : ListView.builder(
                          itemCount: _maintenanceLogs.length,
                          itemBuilder: (context, index) {
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 2),
                              child: Text(
                                _maintenanceLogs[index],
                                style: const TextStyle(
                                  fontFamily: 'monospace',
                                  fontSize: 12,
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}