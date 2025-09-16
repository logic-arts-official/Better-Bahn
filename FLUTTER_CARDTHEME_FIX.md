# Flutter CardTheme Compatibility Fix

## Issue
The Flutter app was failing to build on Windows with the following error:

```
lib/design_system/db_theme.dart(300,16): error GC2F972A8: The argument type 'CardTheme' can't be assigned to the parameter type 'CardThemeData?'
lib/design_system/db_theme.dart(487,16): error GC2F972A8: The argument type 'CardTheme' can't be assigned to the parameter type 'CardThemeData?'
```

## Root Cause
In newer Flutter versions (3.8.1+), the `ThemeData.cardTheme` property expects a `CardThemeData` object instead of a `CardTheme` object. This is a breaking change in the Flutter framework.

## Solution
Changed the constructor calls from `CardTheme(...)` to `CardThemeData(...)` in two locations:

### Before (Lines 300 and 487):
```dart
cardTheme: CardTheme(
  elevation: 2,
  shadowColor: DBColors.dbGray900.withOpacity(0.12),
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(DBBorderRadius.md),
  ),
  color: DBColors.dbBackground,
),
```

### After:
```dart
cardTheme: CardThemeData(
  elevation: 2,
  shadowColor: DBColors.dbGray900.withOpacity(0.12),
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(DBBorderRadius.md),
  ),
  color: DBColors.dbBackground,
),
```

## Validation
- Tested with Flutter 3.27.0 (Dart 3.6.0)
- Ran `flutter analyze` successfully without CardTheme errors
- Confirmed syntax is correct and compatible with modern Flutter versions

## Files Changed
- `flutter-app/lib/design_system/db_theme.dart` (lines 300 and 487)

The app should now build successfully on all platforms including Windows.