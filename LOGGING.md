# Better-Bahn Logging Guide

Better-Bahn now includes comprehensive logging capabilities for both the Python CLI and Flutter mobile app.

## Python CLI Logging

### Features
- **Dual Output**: Logs to both console and file simultaneously
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR
- **File Rotation**: Automatic rotation when files exceed 10MB (keeps 5 backups)
- **Developer Default**: DEBUG level and higher (shows all log messages)

### Configuration

#### Environment Variables
```bash
# Set log level (DEBUG, INFO, WARNING, ERROR)
export BETTER_BAHN_LOG_LEVEL=DEBUG

# Enable/disable file logging
export BETTER_BAHN_FILE_LOGGING=true

# Custom log file path
export BETTER_BAHN_LOG_FILE=my_custom.log

# File rotation settings
export BETTER_BAHN_LOG_MAX_SIZE=10485760  # 10MB in bytes
export BETTER_BAHN_LOG_BACKUP_COUNT=5
```

#### Usage Examples
```bash
# Use default DEBUG logging
uv run main.py "https://www.bahn.de/buchung/start?vbid=example" --age 30

# Use INFO level logging only
BETTER_BAHN_LOG_LEVEL=INFO uv run main.py --help

# Disable file logging (console only)
BETTER_BAHN_FILE_LOGGING=false uv run main.py --help
```

#### Log File Location
- **Default**: `better_bahn.log` in the current directory
- **Custom**: Set via `BETTER_BAHN_LOG_FILE` environment variable
- **Rotation**: Files are rotated as `better_bahn.log.1`, `better_bahn.log.2`, etc.

## Flutter App Logging

### Features
- **Cross-Platform Export**: Works on Android, iOS, Windows, macOS, Linux, and Web
- **Share Integration**: Uses platform-native sharing for maximum compatibility
- **Persistent Storage**: Logs are automatically saved on mobile/desktop platforms
- **User-Friendly**: Simple "Log exportieren" button in the UI

### Usage

1. **View Logs**: Tap "Logs anzeigen/ausblenden" to show/hide the log console
2. **Export Logs**: Tap "Log exportieren" to save and share the log file
3. **Platform Behavior**:
   - **Windows**: Creates `.txt` file that opens in Notepad++ or default text editor
   - **Android/iOS**: Uses system share dialog to save or send via apps
   - **Web**: Triggers browser download of `better_bahn_logs.txt`

### Log File Format
```
Better-Bahn Application Logs
Generated: 2025-09-17T10:30:00.000Z
Platform: Android
--------------------------------------------------

[2025-09-17T10:29:55.000Z] Löse VBID 'abc123' auf...
[2025-09-17T10:29:56.000Z] API-Anfrage gestartet
[2025-09-17T10:29:57.000Z] Verbindungsdetails erhalten
...

--------------------------------------------------
End of log file
```

## Troubleshooting

### Python Logging Issues
```bash
# Check if log file is being created
ls -la better_bahn.log*

# Test logging configuration
python -c "from better_bahn_config import default_config; default_config.setup_logging()"

# Check current configuration
python -c "from better_bahn_config import default_config; print(f'Level: {default_config.logging.log_level}')"
```

### Flutter Logging Issues
- **Export not working**: Check if `share_plus` and `path_provider` packages are installed
- **File not opening**: Ensure the device has a text editor app installed
- **Web download fails**: Check browser settings for download permissions

## Developer Information

### Log Levels
- **DEBUG**: Detailed information for debugging (default)
- **INFO**: General information about program execution
- **WARNING**: Warning messages for unexpected situations
- **ERROR**: Error messages for serious problems

### File Management
- Log files use UTF-8 encoding for proper German character support
- File rotation prevents disk space issues
- Temporary files are cleaned up automatically
- Web downloads use data URLs for broad browser compatibility

### Integration
The logging system integrates with existing Better-Bahn functionality:
- All API calls are logged with timing information
- Error conditions are captured with full context
- User actions in the Flutter app are tracked
- Network failures include detailed error information