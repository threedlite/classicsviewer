#!/bin/bash

# Simple deployment for testing
echo "=== Simple deployment for testing ==="

# 1. Copy database to app assets for testing
echo "Copying database to app assets..."
mkdir -p app/src/main/assets
cp perseus_database/src/main/assets/perseus_texts.db app/src/main/assets/

# 2. Build APK
echo "Building APK..."
./gradlew assembleDebug

# 3. Install
echo "Installing..."
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 4. Clear data
echo "Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug

echo "=== Done! ==="