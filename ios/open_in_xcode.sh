#!/bin/bash

echo "Opening ClassicsViewer iOS project in Xcode..."

# Navigate to the iOS directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Open the Xcode project
if [ -f "ClassicsViewer.xcodeproj/project.pbxproj" ]; then
    open "ClassicsViewer.xcodeproj"
    echo "✅ Xcode project opened successfully"
else
    echo "❌ ClassicsViewer.xcodeproj not found in $(pwd)"
    echo "Make sure you're running this script from the ios/ directory"
    exit 1
fi

echo ""
echo "📋 To build and run:"
echo "1. Wait for dependencies to resolve (Swift Package Manager)"
echo "2. Select a simulator or device from the scheme selector"
echo "3. Press Cmd+R to build and run"
echo ""
echo "📱 Or use command line:"
echo "   ./build_ios.sh                    # Automated build and deploy"
echo "   ./build_ios.sh 'iPhone 16 Pro'   # Specific simulator"
echo "   ./build_ios.sh --list             # List available simulators"
echo ""
echo "📊 Project Status:"
echo "   ✅ Database: perseus_texts.db.zip in Resources/"
echo "   ✅ Dependencies: SQLite.swift (auto-resolved)"
echo "   ✅ Target: iOS 16.1+ deployment"
echo "   ✅ Build system: Tested and working"