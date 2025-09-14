#!/bin/bash
# Factor 5: Build automation script for Better Bahn Flutter app
# Separates build, release, and run processes

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_flutter() {
    if ! command -v flutter &> /dev/null; then
        log_error "Flutter is not installed or not in PATH"
        exit 1
    fi
    
    log_info "Flutter version: $(flutter --version | head -n1)"
}

# Build functions
build_debug() {
    log_info "Building debug APK..."
    cd "$PROJECT_DIR"
    
    flutter build apk \
        --debug \
        --dart-define=ENVIRONMENT=development \
        --dart-define=ENABLE_DEBUG_LOGS=true \
        --dart-define=ENABLE_DEBUG_MENU=true \
        --flavor development
        
    log_info "Debug APK built successfully"
}

build_staging() {
    log_info "Building staging APK..."
    cd "$PROJECT_DIR"
    
    flutter build apk \
        --dart-define=ENVIRONMENT=staging \
        --dart-define=ENABLE_DEBUG_LOGS=true \
        --dart-define=ENABLE_DEBUG_MENU=true \
        --flavor staging
        
    log_info "Staging APK built successfully"
}

build_release() {
    log_info "Building release APK..."
    cd "$PROJECT_DIR"
    
    flutter build apk \
        --release \
        --dart-define=ENVIRONMENT=production \
        --dart-define=ENABLE_DEBUG_LOGS=false \
        --dart-define=ENABLE_DEBUG_MENU=false \
        --dart-define=LOG_LEVEL=error \
        --flavor production
        
    log_info "Release APK built successfully"
}

build_aab() {
    log_info "Building release App Bundle (AAB)..."
    cd "$PROJECT_DIR"
    
    flutter build appbundle \
        --release \
        --dart-define=ENVIRONMENT=production \
        --dart-define=ENABLE_DEBUG_LOGS=false \
        --dart-define=ENABLE_DEBUG_MENU=false \
        --dart-define=LOG_LEVEL=error \
        --flavor production
        
    log_info "Release AAB built successfully"
}

# Analysis and testing
analyze_code() {
    log_info "Running Flutter analyzer..."
    cd "$PROJECT_DIR"
    flutter analyze
}

run_tests() {
    log_info "Running tests..."
    cd "$PROJECT_DIR"
    flutter test
}

# Clean build artifacts
clean_build() {
    log_info "Cleaning build artifacts..."
    cd "$PROJECT_DIR"
    flutter clean
    rm -rf build/
    log_info "Build artifacts cleaned"
}

# Main script logic
main() {
    log_info "Better Bahn Build Script"
    log_info "========================"
    
    check_flutter
    
    case "${1:-help}" in
        "debug")
            analyze_code
            build_debug
            ;;
        "staging")
            analyze_code
            build_staging
            ;;
        "release")
            analyze_code
            run_tests
            build_release
            ;;
        "aab")
            analyze_code
            run_tests
            build_aab
            ;;
        "clean")
            clean_build
            ;;
        "analyze")
            analyze_code
            ;;
        "test")
            run_tests
            ;;
        "help"|*)
            echo "Usage: $0 {debug|staging|release|aab|clean|analyze|test}"
            echo ""
            echo "Commands:"
            echo "  debug    - Build debug APK with development configuration"
            echo "  staging  - Build staging APK with staging configuration"
            echo "  release  - Build release APK with production configuration"
            echo "  aab      - Build release App Bundle (AAB) for Play Store"
            echo "  clean    - Clean all build artifacts"
            echo "  analyze  - Run Flutter analyzer"
            echo "  test     - Run tests"
            echo "  help     - Show this help message"
            ;;
    esac
}

main "$@"