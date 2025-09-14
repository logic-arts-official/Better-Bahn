# Better Bahn ProGuard Configuration
# Factor 5: Build/Release/Run separation - Production optimizations

# Keep Flutter engine classes
-keep class io.flutter.** { *; }
-keep class io.flutter.embedding.** { *; }

# Keep application classes
-keep class com.logicarts.betterbahn.** { *; }

# Preserve line numbers for debugging
-keepattributes SourceFile,LineNumberTable

# Keep standard Android classes
-keep class androidx.** { *; }
-keep class android.** { *; }

# HTTP client optimizations
-keep class okhttp3.** { *; }
-keep class retrofit2.** { *; }

# JSON serialization
-keepattributes Signature
-keepattributes *Annotation*

# Remove debug logs in release
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
}