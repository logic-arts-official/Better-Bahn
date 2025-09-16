/// Deutsche Bahn Design System v3.1.1 Implementation
/// 
/// This file implements the core theme and design tokens from the 
/// DB UX Design System v3.1.1 (latest stable version)
/// https://design-system.deutschebahn.com/
/// 
/// Updated to use Flutter default fonts with Google Fonts Lato

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// DB Design System Color Tokens v3.1.1
class DBColors {
  // Primary Colors
  static const Color dbRed = Color(0xFFEC0016);
  static const Color dbRedLight = Color(0xFFFF6B8A);
  static const Color dbRedDark = Color(0xFFB10010);
  
  // Secondary Colors  
  static const Color dbBlue = Color(0xFF0078D2);
  static const Color dbBlueLight = Color(0xFF64B5F6);
  static const Color dbBlueDark = Color(0xFF005A9F);
  
  // Neutral Colors
  static const Color dbGray100 = Color(0xFFF7F7F7);
  static const Color dbGray200 = Color(0xFFECECEC);
  static const Color dbGray300 = Color(0xFFD6D6D6);
  static const Color dbGray400 = Color(0xFFB3B3B3);
  static const Color dbGray500 = Color(0xFF878787);
  static const Color dbGray600 = Color(0xFF646464);
  static const Color dbGray700 = Color(0xFF3C3C3C);
  static const Color dbGray800 = Color(0xFF282828);
  static const Color dbGray900 = Color(0xFF1C1C1C);
  
  // Semantic Colors
  static const Color dbSuccess = Color(0xFF00B04F);
  static const Color dbWarning = Color(0xFFFFB700);
  static const Color dbError = Color(0xFFD52B1E);
  static const Color dbInfo = Color(0xFF0078D2);
  
  // Background Colors
  static const Color dbBackground = Color(0xFFFFFFFF);
  static const Color dbBackgroundDark = Color(0xFF1C1C1C);
  static const Color dbSurface = Color(0xFFF7F7F7);
  static const Color dbSurfaceDark = Color(0xFF282828);
}

/// DB Design System Typography v3.1.1
/// Updated to use Google Fonts Lato instead of proprietary DB fonts
class DBTextStyles {
  // Using Google Fonts Lato for all text styles
  static TextStyle get _baseTextStyle => GoogleFonts.lato();
  static TextStyle get _headingTextStyle => GoogleFonts.lato(fontWeight: FontWeight.w700);
  
  // Display Styles (Using Lato Bold for headlines)
  static TextStyle get displayLarge => _headingTextStyle.copyWith(
    fontSize: 57,
    fontWeight: FontWeight.w700,
    height: 1.12,
    letterSpacing: -0.25,
  );
  
  static TextStyle get displayMedium => _headingTextStyle.copyWith(
    fontSize: 45,
    fontWeight: FontWeight.w700,
    height: 1.16,
  );
  
  static TextStyle get displaySmall => _headingTextStyle.copyWith(
    fontSize: 36,
    fontWeight: FontWeight.w700,
    height: 1.22,
  );
  
  // Headline Styles (Using Lato Bold)
  static TextStyle get headlineLarge => _headingTextStyle.copyWith(
    fontSize: 32,
    fontWeight: FontWeight.w700,
    height: 1.25,
  );
  
  static TextStyle get headlineMedium => _headingTextStyle.copyWith(
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.29,
  );
  
  static TextStyle get headlineSmall => _headingTextStyle.copyWith(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    height: 1.33,
  );
  
  // Title Styles (Using Lato SemiBold)
  static TextStyle get titleLarge => _baseTextStyle.copyWith(
    fontSize: 22,
    fontWeight: FontWeight.w600,
    height: 1.27,
  );
  
  static TextStyle get titleMedium => _baseTextStyle.copyWith(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    height: 1.50,
    letterSpacing: 0.15,
  );
  
  static TextStyle get titleSmall => _baseTextStyle.copyWith(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.43,
    letterSpacing: 0.1,
  );
  
  // Body Styles (Using Lato Regular)
  static TextStyle get bodyLarge => _baseTextStyle.copyWith(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.50,
    letterSpacing: 0.5,
  );
  
  static TextStyle get bodyMedium => _baseTextStyle.copyWith(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.43,
    letterSpacing: 0.25,
  );
  
  static TextStyle get bodySmall => _baseTextStyle.copyWith(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.33,
    letterSpacing: 0.4,
  );
  
  // Label Styles (Using Lato SemiBold)
  static TextStyle get labelLarge => _baseTextStyle.copyWith(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.43,
    letterSpacing: 0.1,
  );
  
  static TextStyle get labelMedium => _baseTextStyle.copyWith(
    fontSize: 12,
    fontWeight: FontWeight.w600,
    height: 1.33,
    letterSpacing: 0.5,
  );
  
  static TextStyle get labelSmall => _baseTextStyle.copyWith(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.45,
    letterSpacing: 0.5,
  );
}

/// DB Design System Spacing Scale v3.1.1
class DBSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
  static const double xxxl = 64.0;
}

/// DB Design System Elevation/Shadow Tokens
class DBElevation {
  static const List<BoxShadow> level1 = [
    BoxShadow(
      color: Color(0x1F000000),
      offset: Offset(0, 1),
      blurRadius: 3,
      spreadRadius: 0,
    ),
  ];
  
  static const List<BoxShadow> level2 = [
    BoxShadow(
      color: Color(0x1F000000),
      offset: Offset(0, 2),
      blurRadius: 6,
      spreadRadius: 0,
    ),
  ];
  
  static const List<BoxShadow> level3 = [
    BoxShadow(
      color: Color(0x1F000000),
      offset: Offset(0, 4),
      blurRadius: 12,
      spreadRadius: 0,
    ),
  ];
}

/// DB Design System Border Radius Tokens
class DBBorderRadius {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 24.0;
  static const double pill = 1000.0; // Creates pill shape
}

/// Main DB Theme Configuration for Material 3
class DBTheme {
  static ThemeData get lightTheme => ThemeData(
    useMaterial3: true,
    textTheme: GoogleFonts.latoTextTheme(),
    
    // Color Scheme
    colorScheme: const ColorScheme.light(
      primary: DBColors.dbRed,
      onPrimary: Colors.white,
      primaryContainer: DBColors.dbRedLight,
      onPrimaryContainer: DBColors.dbRedDark,
      
      secondary: DBColors.dbBlue,
      onSecondary: Colors.white,
      secondaryContainer: DBColors.dbBlueLight,
      onSecondaryContainer: DBColors.dbBlueDark,
      
      surface: DBColors.dbBackground,
      onSurface: DBColors.dbGray900,
      surfaceVariant: DBColors.dbSurface,
      onSurfaceVariant: DBColors.dbGray700,
      
      background: DBColors.dbBackground,
      onBackground: DBColors.dbGray900,
      
      error: DBColors.dbError,
      onError: Colors.white,
      
      outline: DBColors.dbGray400,
      outlineVariant: DBColors.dbGray300,
      
      shadow: DBColors.dbGray900,
      scrim: DBColors.dbGray900,
      
      inverseSurface: DBColors.dbGray900,
      onInverseSurface: DBColors.dbGray100,
      inversePrimary: DBColors.dbRedLight,
    ),
    
    // Typography using DB Design System styles with Google Fonts Lato
    textTheme: TextTheme(
      displayLarge: DBTextStyles.displayLarge,
      displayMedium: DBTextStyles.displayMedium,
      displaySmall: DBTextStyles.displaySmall,
      
      headlineLarge: DBTextStyles.headlineLarge,
      headlineMedium: DBTextStyles.headlineMedium,
      headlineSmall: DBTextStyles.headlineSmall,
      
      titleLarge: DBTextStyles.titleLarge,
      titleMedium: DBTextStyles.titleMedium,
      titleSmall: DBTextStyles.titleSmall,
      
      bodyLarge: DBTextStyles.bodyLarge,
      bodyMedium: DBTextStyles.bodyMedium,
      bodySmall: DBTextStyles.bodySmall,
      
      labelLarge: DBTextStyles.labelLarge,
      labelMedium: DBTextStyles.labelMedium,
      labelSmall: DBTextStyles.labelSmall,
    ),
    
    // App Bar Theme
    appBarTheme: AppBarTheme(
      backgroundColor: DBColors.dbRed,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: GoogleFonts.lato(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: Colors.white,
      ),
    ),
    
    // Card Theme
    cardTheme: CardThemeData(
      elevation: 2,
      shadowColor: DBColors.dbGray900.withOpacity(0.12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.md),
      ),
      color: DBColors.dbBackground,
    ),
    
    // Input Decoration Theme
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        borderSide: const BorderSide(color: DBColors.dbGray400),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        borderSide: const BorderSide(color: DBColors.dbGray400),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        borderSide: const BorderSide(color: DBColors.dbRed, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        borderSide: const BorderSide(color: DBColors.dbError),
      ),
      contentPadding: const EdgeInsets.all(DBSpacing.md),
      filled: true,
      fillColor: DBColors.dbBackground,
    ),
    
    // Elevated Button Theme
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: DBColors.dbRed,
        foregroundColor: Colors.white,
        elevation: 2,
        padding: const EdgeInsets.symmetric(
          horizontal: DBSpacing.lg,
          vertical: DBSpacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
        textStyle: DBTextStyles.labelLarge.copyWith(color: Colors.white),
      ),
    ),
    
    // Text Button Theme  
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: DBColors.dbRed,
        padding: const EdgeInsets.symmetric(
          horizontal: DBSpacing.md,
          vertical: DBSpacing.sm,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
        textStyle: DBTextStyles.labelLarge.copyWith(color: DBColors.dbRed),
      ),
    ),
    
    // Outlined Button Theme
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: DBColors.dbRed,
        side: const BorderSide(color: DBColors.dbRed),
        padding: const EdgeInsets.symmetric(
          horizontal: DBSpacing.lg,
          vertical: DBSpacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
        textStyle: DBTextStyles.labelLarge.copyWith(color: DBColors.dbRed),
      ),
    ),
    
    // Checkbox Theme
    checkboxTheme: CheckboxThemeData(
      fillColor: MaterialStateProperty.resolveWith<Color>((states) {
        if (states.contains(MaterialState.selected)) {
          return DBColors.dbRed;
        }
        return Colors.transparent;
      }),
      checkColor: MaterialStateProperty.all(Colors.white),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.xs),
      ),
    ),
    
    // Progress Indicator Theme
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: DBColors.dbRed,
      linearTrackColor: DBColors.dbGray300,
    ),
    
    // Snack Bar Theme
    snackBarTheme: SnackBarThemeData(
      backgroundColor: DBColors.dbGray800,
      contentTextStyle: DBTextStyles.bodyMedium.copyWith(color: Colors.white),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.sm),
      ),
      behavior: SnackBarBehavior.floating,
    ),
  );
  
  static ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    
    // Dark Color Scheme
    colorScheme: const ColorScheme.dark(
      primary: DBColors.dbRedLight,
      onPrimary: DBColors.dbGray900,
      primaryContainer: DBColors.dbRedDark,
      onPrimaryContainer: DBColors.dbRedLight,
      
      secondary: DBColors.dbBlueLight,
      onSecondary: DBColors.dbGray900,
      secondaryContainer: DBColors.dbBlueDark,
      onSecondaryContainer: DBColors.dbBlueLight,
      
      surface: DBColors.dbBackgroundDark,
      onSurface: DBColors.dbGray100,
      surfaceVariant: DBColors.dbSurfaceDark,
      onSurfaceVariant: DBColors.dbGray300,
      
      background: DBColors.dbBackgroundDark,
      onBackground: DBColors.dbGray100,
      
      error: DBColors.dbError,
      onError: Colors.white,
      
      outline: DBColors.dbGray600,
      outlineVariant: DBColors.dbGray700,
      
      shadow: Colors.black,
      scrim: Colors.black,
      
      inverseSurface: DBColors.dbGray100,
      onInverseSurface: DBColors.dbGray900,
      inversePrimary: DBColors.dbRed,
    ),
    
    // Same typography as light theme with Google Fonts Lato
    textTheme: TextTheme(
      displayLarge: DBTextStyles.displayLarge,
      displayMedium: DBTextStyles.displayMedium,
      displaySmall: DBTextStyles.displaySmall,
      
      headlineLarge: DBTextStyles.headlineLarge,
      headlineMedium: DBTextStyles.headlineMedium,
      headlineSmall: DBTextStyles.headlineSmall,
      
      titleLarge: DBTextStyles.titleLarge,
      titleMedium: DBTextStyles.titleMedium,
      titleSmall: DBTextStyles.titleSmall,
      
      bodyLarge: DBTextStyles.bodyLarge,
      bodyMedium: DBTextStyles.bodyMedium,
      bodySmall: DBTextStyles.bodySmall,
      
      labelLarge: DBTextStyles.labelLarge,
      labelMedium: DBTextStyles.labelMedium,
      labelSmall: DBTextStyles.labelSmall,
    ),
    
    // Dark theme app bar
    appBarTheme: AppBarTheme(
      backgroundColor: DBColors.dbBackgroundDark,
      foregroundColor: DBColors.dbGray100,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: GoogleFonts.lato(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: DBColors.dbGray100,
      ),
    ),
    
    // Dark theme components follow similar pattern...
    cardTheme: CardThemeData(
      elevation: 2,
      shadowColor: Colors.black.withOpacity(0.3),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.md),
      ),
      color: DBColors.dbSurfaceDark,
    ),
  );
}