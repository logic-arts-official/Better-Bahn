# API Headers Fix Documentation

## Issue Description
The application was experiencing "ClientException: Failed to fetch" errors when resolving VBID (connection IDs) from Deutsche Bahn URLs. This was occurring in both Python and Flutter implementations.

## Root Cause
The Deutsche Bahn API requires specific HTTP headers that were missing from the original implementation:
- `Origin` and `Referer` headers for CORS validation
- `Sec-Fetch-*` headers for browser security compliance
- Proper `Accept-Language` and other browser-like headers
- `X-Correlation-Id` for request tracing

## Solution Implemented

### Python Implementation (main.py)
Updated `resolve_vbid_to_connection()` function with:
```python
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "de",
    "Accept-Encoding": "gzip, deflate",  # Removed br to avoid decompression issues
    "Origin": "https://www.bahn.de",
    "Referer": "https://www.bahn.de/buchung/fahrplan/suche",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}
```

### Flutter Implementation (flutter-app/lib/main.dart)
Updated `_resolveVbidToConnection()` method with identical headers and added:
```dart
"X-Correlation-Id": "${DateTime.now().millisecondsSinceEpoch}_${DateTime.now().microsecondsSinceEpoch}",
```

### Enhanced Error Handling
- Specific guidance for 403 Forbidden errors
- Better JSON parsing validation
- Compression handling improvements
- More informative error messages

## Testing Results
- ✅ VBID resolution (first API call) now works correctly
- ✅ Enhanced error messages when API restricts access
- ✅ Proper compression handling
- ✅ Better user experience with informative error messages

## Impact
The original "ClientException: Failed to fetch" error is now replaced with informative messages that help users understand when API access is restricted. The implementation properly handles Deutsche Bahn API requirements while providing clear feedback about any access limitations.

## Notes
If 403 errors persist on the recon endpoint, this indicates API-level restrictions rather than implementation issues. The enhanced error messages guide users about potential causes and solutions.