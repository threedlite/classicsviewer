#!/bin/bash
# Quick deploy script for Classics Viewer

echo "🚀 Building and deploying Classics Viewer..."

# Build
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Install
    ./platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
    
    if [ $? -eq 0 ]; then
        echo "✅ App installed successfully!"
        
        # Launch app
        ./platform-tools/adb shell am start -n com.perseus.viewer.debug/com.perseus.viewer.MainActivity
        echo "✅ App launched!"
    else
        echo "❌ Installation failed"
    fi
else
    echo "❌ Build failed"
fi