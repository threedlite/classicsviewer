#!/bin/bash
set -e

# Quick Redeploy Script for iOS Classics Viewer
# For use after making code changes - does incremental build and redeploy
# Much faster than full build_ios.sh

# Configuration
SCHEME="ClassicsViewer"
PROJECT="ClassicsViewer.xcodeproj"
DEFAULT_SIMULATOR="iPhone 16"
BUNDLE_ID="com.classicsviewer.app"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Quick Redeploy - iOS Classics Viewer${NC}"

SIMULATOR="${1:-$DEFAULT_SIMULATOR}"

# Navigate to iOS directory
cd "$(dirname "$0")"

# Ensure simulator is running
xcrun simctl boot "$SIMULATOR" 2>/dev/null || true

# Quick incremental build (no clean)
echo -e "${BLUE}🔨 Building (incremental)...${NC}"
xcodebuild -scheme "$SCHEME" \
    -project "$PROJECT" \
    -destination "platform=iOS Simulator,name=$SIMULATOR" \
    build -quiet

# Find the built app
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" 2>/dev/null | head -1)

# Terminate existing app if running
echo -e "${BLUE}🔄 Redeploying...${NC}"
xcrun simctl terminate booted "$BUNDLE_ID" 2>/dev/null || true

# Quick reinstall (uninstall + install)
xcrun simctl uninstall booted "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl install booted "$APP_PATH"

# Launch the app
PID=$(xcrun simctl launch booted "$BUNDLE_ID" 2>/dev/null)

echo -e "${GREEN}✅ Redeployed! PID: $PID${NC}"
echo -e "${BLUE}📱 App is running on $SIMULATOR${NC}"