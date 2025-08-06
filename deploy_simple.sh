#!/bin/bash

# Simple deployment for testing with Play Asset Delivery
echo "=== Automated Deployment for Classics Viewer ==="

# 1. Copy compressed database to debug assets for local testing
echo "Copying compressed database to debug assets..."
mkdir -p app/src/debug/assets
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/

# 2. Build and install debug APK
echo "Building and installing debug APK..."
./gradlew installDebug

# 3. Clear app data for fresh start
echo "Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug

echo "=== Deployment Complete! ==="
echo "The app will extract the database on first launch (~6-7 seconds)"