#!/bin/bash

# Simple deployment for testing with Play Asset Delivery
echo "=== Automated Deployment for Classics Viewer ==="

# 1. Verify and prepare database for debug assets
echo "Verifying database in debug assets..."
if [ ! -f "app/src/debug/assets/perseus_texts.db.zip" ]; then
    echo "Error: Database not found in app/src/debug/assets/"
    echo "Run deploy_complete.sh to build the database first"
    exit 1
fi

# 1a. Ensure the ZIP contains correctly named database file
echo "Checking database ZIP contents..."
ZIP_CONTENTS=$(unzip -l app/src/debug/assets/perseus_texts.db.zip | grep -E "perseus_texts\.db$|perseus_texts_sample\.db$")
if echo "$ZIP_CONTENTS" | grep -q "perseus_texts_sample.db"; then
    echo "Fixing database filename in ZIP..."
    cd data-prep
    # Extract the sample database
    unzip -o ../app/src/debug/assets/perseus_texts.db.zip perseus_texts_sample.db
    # Rename to expected name
    mv perseus_texts_sample.db perseus_texts.db
    # Create new ZIP with correct name
    zip -9 perseus_texts.db.zip perseus_texts.db
    # Copy to both locations
    cp perseus_texts.db.zip ../app/src/debug/assets/
    cp perseus_texts.db.zip ../perseus_database/src/main/assets/
    # Clean up
    rm perseus_texts.db
    cd ..
    echo "✓ Database ZIP fixed"
fi

# 2. Build and install debug APK (disable incremental builds to ensure latest database)
echo "Building and installing debug APK..."
./gradlew installDebug --no-build-cache --rerun-tasks

# 3. Clear app data for fresh start
echo "Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug

echo "=== Deployment Complete! ==="
echo "The app will extract the database on first launch (~6-7 seconds)"