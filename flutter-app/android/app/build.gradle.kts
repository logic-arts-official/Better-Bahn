plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.logicarts.betterbahn"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        // Updated application ID to follow proper naming convention
        applicationId = "com.logicarts.betterbahn"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        
        // Factor 10: Dev/Prod Parity - Ensure same targetSdk across environments
        // Factor 3: Build-time configuration injection via dart-define
        buildConfigField "String", "BUILD_CONFIG_ENVIRONMENT", "\"${project.findProperty('dart.env.ENVIRONMENT') ?: 'development'}\""
        buildConfigField "String", "BUILD_CONFIG_VERSION", "\"${project.findProperty('dart.env.VERSION') ?: '1.0.0'}\""
    }

    // Factor 3: Config - Environment-specific build types
    buildTypes {
        debug {
            debuggable true
            minifyEnabled false
            signingConfig signingConfigs.debug
            applicationIdSuffix ".debug"
        }
        
        release {
            // Factor 5: Build/Release separation
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
        
        // Factor 10: Dev/Prod Parity - Staging environment
        create("staging") {
            initWith debug
            applicationIdSuffix ".staging"
            debuggable false
        }
    }
    
    // Factor 10: Consistent build configuration
    flavorDimensions += "environment"
    productFlavors {
        development {
            dimension "environment"
            applicationIdSuffix ".dev"
        }
        
        staging {
            dimension "environment"
            applicationIdSuffix ".staging"
        }
        
        production {
            dimension "environment"
        }
    }
}

flutter {
    source = "../.."
}
