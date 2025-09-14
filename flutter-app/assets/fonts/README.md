# DB Fonts Directory

This directory should contain the official Deutsche Bahn font files:

## Required Font Files

### DB Sans (Primary Font)
- `DBSans-Regular.ttf` (400 weight)
- `DBSans-Medium.ttf` (500 weight)  
- `DBSans-SemiBold.ttf` (600 weight)
- `DBSans-Bold.ttf` (700 weight)

### DB Head (Display Font)
- `DBHead-Regular.ttf` (400 weight)
- `DBHead-Bold.ttf` (700 weight)

## Font Licensing

**Important**: DB Sans and DB Head are proprietary fonts owned by Deutsche Bahn AG. 

To use these fonts in production, you must:
1. Obtain proper licensing from Deutsche Bahn
2. Follow their brand guidelines and usage terms
3. Ensure compliance with their font licensing agreements

## Development Fallback

During development, if the DB fonts are not available:
- The app will fall back to system fonts (typically Roboto on Android, San Francisco on iOS)
- All typography sizing and spacing will remain consistent
- The visual hierarchy will be preserved

## Font Installation

1. Obtain the official font files from Deutsche Bahn
2. Place them in this directory (`assets/fonts/`)
3. Ensure the file names match those specified in `pubspec.yaml`
4. Run `flutter clean` and `flutter pub get` to refresh assets
5. Rebuild the app to load the new fonts

## Alternative for Testing

For testing purposes without access to official DB fonts, you can:
1. Use Google Fonts' similar fonts as placeholders
2. Download open-source alternatives that approximate the DB font styles
3. Test the layout and functionality with system fonts

The design system will work correctly regardless of font availability, ensuring the app remains functional while maintaining the DB visual design principles.