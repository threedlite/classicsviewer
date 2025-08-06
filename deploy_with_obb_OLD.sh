#!/bin/bash

# Deploy app with OBB file

PACKAGE_NAME="com.classicsviewer.app"
OBB_NAME="main.1.$PACKAGE_NAME.obb"

echo "Deploying Classics Viewer with OBB..."

# Check if OBB exists
if [ ! -f "$OBB_NAME" ]; then
    echo "OBB file not found. Creating it..."
    ./create_obb.sh
fi

# Install APK
echo "Installing APK..."
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Create OBB directory on device
echo "Creating OBB directory on device..."
adb shell mkdir -p /sdcard/Android/obb/$PACKAGE_NAME/

# Push OBB file
echo "Pushing OBB file to device..."
adb push $OBB_NAME /sdcard/Android/obb/$PACKAGE_NAME/

# Verify OBB installation
echo ""
echo "Verifying OBB installation..."
OBB_SIZE=$(adb shell ls -l /sdcard/Android/obb/$PACKAGE_NAME/$OBB_NAME | awk '{print $5}')
if [ -n "$OBB_SIZE" ] && [ "$OBB_SIZE" -gt 0 ]; then
    echo "✓ OBB file installed successfully (size: $OBB_SIZE bytes)"
else
    echo "✗ OBB file installation failed"
fi

echo ""
echo "Deployment complete!"
echo "The app will use the OBB file on first launch."