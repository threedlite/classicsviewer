#!/bin/bash
set -e

# iOS Classics Viewer Build and Deploy Script
# Builds the app and deploys it to iOS Simulator
# Tested and working as of 2025-08-12

# Configuration
SCHEME="ClassicsViewer"
PROJECT="ClassicsViewer.xcodeproj"
DEFAULT_SIMULATOR="iPhone 16"
BUNDLE_ID="com.classicsviewer.app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_usage() {
    echo "Usage: $0 [SIMULATOR_NAME]"
    echo ""
    echo "Examples:"
    echo "  $0                    # Use default iPhone 16"
    echo "  $0 'iPhone 16 Pro'   # Use specific simulator"
    echo "  $0 --list             # List available simulators"
    echo ""
}

list_simulators() {
    log_info "Available iPhone simulators:"
    xcrun simctl list devices iPhone | grep -E "iPhone.*\(" | sed 's/^[ ]*/- /'
}

# Parse arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

if [ "$1" = "--list" ] || [ "$1" = "-l" ]; then
    list_simulators
    exit 0
fi

SIMULATOR="${1:-$DEFAULT_SIMULATOR}"

log_info "Building iOS Classics Viewer..."
log_info "Target Simulator: $SIMULATOR"

# Navigate to iOS directory (handle both direct execution and sourcing)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "Working directory: $(pwd)"

# iOS uses a specific database built from IOS_SAMPLE_AUTHORS.csv
DATABASE_SOURCE="../data-prep/perseus_texts_ios.db.zip"
DATABASE_DEST="ClassicsViewer/Resources/perseus_texts.db.zip"
IOS_AUTHORS_CSV="../data-prep/IOS_SAMPLE_AUTHORS.csv"

# Always rebuild database if IOS_SAMPLE_AUTHORS.csv is newer than the zip
if [ -f "$IOS_AUTHORS_CSV" ]; then
    if [ ! -f "$DATABASE_SOURCE" ] || [ "$IOS_AUTHORS_CSV" -nt "$DATABASE_SOURCE" ]; then
        log_info "Building iOS database from IOS_SAMPLE_AUTHORS.csv..."
        log_warning "This will take 2-3 minutes..."
        (cd ../data-prep && python3 create_perseus_database.py sample IOS_SAMPLE_AUTHORS.csv ios)
        if [ $? -ne 0 ]; then
            log_error "Failed to build iOS database"
            exit 1
        fi
        log_success "iOS database built successfully"
    fi
fi

if [ ! -f "$DATABASE_DEST" ] || [ "$DATABASE_SOURCE" -nt "$DATABASE_DEST" ]; then
    if [ -f "$DATABASE_SOURCE" ]; then
        log_info "Copying iOS database from data-prep..."
        mkdir -p "ClassicsViewer/Resources"
        cp "$DATABASE_SOURCE" "$DATABASE_DEST"
        log_success "Database copied successfully"
    else
        log_error "iOS database source not found at: $DATABASE_SOURCE"
        log_error "Please build the iOS database first:"
        log_error "  cd ../data-prep && python3 create_perseus_database.py sample IOS_SAMPLE_AUTHORS.csv ios"
        exit 1
    fi
else
    log_info "iOS database already up-to-date at $DATABASE_DEST"
fi

# Copy audio file if needed
AUDIO_SOURCE="../audio/homer_iliad_chamberlain_audio_7.zip"
AUDIO_DEST="ClassicsViewer/Resources/homer_iliad_chamberlain_audio_7.zip"

if [ ! -f "$AUDIO_DEST" ]; then
    if [ -f "$AUDIO_SOURCE" ]; then
        log_info "Copying audio file from audio directory..."
        cp "$AUDIO_SOURCE" "$AUDIO_DEST"
        log_success "Audio file copied successfully"
    else
        log_warning "Audio file not found at: $AUDIO_SOURCE (optional)"
    fi
else
    log_info "Audio file already exists at $AUDIO_DEST"
fi

# Generate Xcode project if it doesn't exist
if [ ! -d "$PROJECT" ]; then
    log_info "Xcode project not found, generating with XcodeGen..."
    if command -v xcodegen >/dev/null 2>&1; then
        xcodegen generate
        if [ -d "$PROJECT" ]; then
            log_success "Xcode project generated successfully"
        else
            log_error "Failed to generate Xcode project"
            exit 1
        fi
    else
        log_error "XcodeGen is not installed. Install it with: brew install xcodegen"
        exit 1
    fi
fi

# Check if we're in the right directory
if [ ! -d "$PROJECT" ]; then
    log_error "Project file '$PROJECT' not found in $(pwd)"
    log_error "Make sure you're running this script from the ios/ directory"
    exit 1
fi

# Check if simulator exists
log_info "Checking if simulator '$SIMULATOR' exists..."
if ! xcrun simctl list devices | grep -q "$SIMULATOR"; then
    log_error "Simulator '$SIMULATOR' not found."
    echo ""
    log_info "Available simulators:"
    list_simulators
    exit 1
fi

# Boot simulator if not already running
log_info "Booting simulator: $SIMULATOR"
if xcrun simctl boot "$SIMULATOR" 2>/dev/null; then
    log_success "Simulator booted successfully"
else
    log_warning "Simulator was already running or failed to boot"
fi

# Open Simulator app
log_info "Opening Simulator app..."
open -a Simulator

# Give simulator a moment to fully boot
sleep 2

# Skip clean for faster incremental builds
# Uncomment the following if you need a clean build:
# log_info "Cleaning previous build..."
# xcodebuild -scheme "$SCHEME" \
#     -project "$PROJECT" \
#     -destination "platform=iOS Simulator,name=$SIMULATOR" \
#     clean > /dev/null 2>&1 || log_warning "Clean failed, continuing anyway"

# Build the app
log_info "Building app for $SIMULATOR..."
if xcodebuild -scheme "$SCHEME" \
    -project "$PROJECT" \
    -destination "platform=iOS Simulator,name=$SIMULATOR" \
    build; then
    log_success "Build completed successfully"
else
    log_error "Build failed"
    exit 1
fi

# Find the built app
log_info "Locating built app..."
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" 2>/dev/null | head -1)

if [ -z "$APP_PATH" ]; then
    log_error "Could not find built app in DerivedData"
    log_error "Expected path pattern: ~/Library/Developer/Xcode/DerivedData/*/Build/Products/Debug-iphonesimulator/ClassicsViewer.app"
    exit 1
fi

log_success "Found app at: $APP_PATH"

# Verify the app file exists and is valid
if [ ! -d "$APP_PATH" ]; then
    log_error "App bundle not found or invalid: $APP_PATH"
    exit 1
fi

# Uninstall previous version to ensure clean deployment
log_info "Uninstalling previous version (if exists)..."
xcrun simctl uninstall booted "$BUNDLE_ID" 2>/dev/null || log_info "No previous installation found"

# Install the app
log_info "Installing app on simulator..."
if xcrun simctl install booted "$APP_PATH"; then
    log_success "App installed successfully"
else
    log_error "Failed to install app"
    exit 1
fi

# Launch the app
log_info "Launching app..."
PID=$(xcrun simctl launch booted "$BUNDLE_ID" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$PID" ]; then
    log_success "App launched successfully!"
    log_success "Process ID: $PID"
    log_success "App is running on '$SIMULATOR' simulator"
    echo ""
    log_info "You can now test the app in the iOS Simulator"
    
    # Show verification commands
    echo ""
    log_info "Verification commands:"
    echo "  # Check if app is installed:"
    echo "  xcrun simctl listapps booted | grep classicsviewer"
    echo ""
    echo "  # Monitor app logs:"
    echo "  xcrun simctl spawn booted log stream --predicate 'processImagePath contains \"ClassicsViewer\"'"
    echo ""
    echo "  # Get app container path:"
    echo "  xcrun simctl get_app_container booted com.classicsviewer.app"
    
else
    log_error "Failed to launch app"
    log_info "Trying to get more info..."
    
    # Check if app is installed
    if xcrun simctl listapps booted | grep -q "$BUNDLE_ID"; then
        log_warning "App is installed but failed to launch"
        log_info "Try launching manually from the simulator"
    else
        log_error "App is not properly installed"
    fi
    
    exit 1
fi

log_success "Build and deployment complete!"