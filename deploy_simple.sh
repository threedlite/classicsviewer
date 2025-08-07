#!/bin/bash

# Simple deployment for testing with Play Asset Delivery
echo "=== Automated Deployment for Classics Viewer ==="

# 1. Verify database exists in debug assets
echo "Verifying database in debug assets..."
if [ ! -f "app/src/debug/assets/perseus_texts.db.zip" ]; then
    echo "Error: Database not found in app/src/debug/assets/"
    echo "Run deploy_complete.sh to build the database first"
    exit 1
fi

# 2. Build and install debug APK
echo "Building and installing debug APK..."
./gradlew installDebug

# 3. Clear app data for fresh start
echo "Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug

echo "=== Deployment Complete! ==="
echo "The app will extract the database on first launch (~6-7 seconds)"