#!/bin/bash

# Script to build a signed AAB (Android App Bundle) for Google Play release

set -e

echo "========================================="
echo "Building Classics Viewer Release AAB"
echo "========================================="

# Check if keystore.properties exists
if [ ! -f "keystore.properties" ]; then
    echo ""
    echo "ERROR: keystore.properties not found!"
    echo ""
    echo "Please create keystore.properties with:"
    echo "  storePassword=YOUR_KEYSTORE_PASSWORD"
    echo "  keyPassword=YOUR_KEY_PASSWORD"  
    echo "  keyAlias=classics-viewer-key"
    echo "  storeFile=keystore/release-keystore.jks"
    echo ""
    echo "If you haven't created a keystore yet, run:"
    echo "  ./create_release_keystore.sh"
    exit 1
fi

# Check if keystore file exists
KEYSTORE_FILE=$(grep storeFile keystore.properties | cut -d'=' -f2)
if [ ! -f "app/$KEYSTORE_FILE" ]; then
    echo "ERROR: Keystore file not found at app/$KEYSTORE_FILE"
    echo "Please run ./create_release_keystore.sh first"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
./gradlew clean

# Build the AAB
echo "Building release AAB..."
./gradlew bundleRelease

# Check if build succeeded
if [ $? -eq 0 ]; then
    AAB_FILE="app/build/outputs/bundle/release/app-release.aab"
    
    if [ -f "$AAB_FILE" ]; then
        # Get file size
        SIZE=$(du -h "$AAB_FILE" | cut -f1)
        
        echo ""
        echo "✓ BUILD SUCCESSFUL!"
        echo "========================================="
        echo "AAB file: $AAB_FILE"
        echo "Size: $SIZE"
        echo ""
        echo "This AAB is ready to upload to Google Play Console."
        echo ""
        echo "NEXT STEPS:"
        echo "1. Go to https://play.google.com/console"
        echo "2. Create a new app or select existing"
        echo "3. Go to Release > Production"
        echo "4. Create new release and upload the AAB"
        echo ""
        echo "NOTES:"
        echo "- The AAB includes the asset pack with the database"
        echo "- No separate OBB file needed (using Play Asset Delivery)"
        echo "- Sample database is included for initial release"
        echo "========================================="
        
        # Copy AAB to a convenient location
        cp "$AAB_FILE" "classics-viewer-release-v1.0.aab"
        echo ""
        echo "AAB also copied to: classics-viewer-release-v1.0.aab"
    else
        echo "ERROR: AAB file not found at expected location"
        exit 1
    fi
else
    echo "BUILD FAILED!"
    exit 1
fi