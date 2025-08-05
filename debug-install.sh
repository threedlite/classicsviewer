#!/bin/bash

# Debug installation script for Classics Viewer
# Connects to phone at 192.168.4.209:45739

PHONE_IP="192.168.4.209:45739"
APK_PATH="app/build/outputs/apk/debug/app-debug.apk"

echo "Classics Viewer Debug Installation Script"
echo "========================================"

# Connect to device
echo "Connecting to device at $PHONE_IP..."
adb connect $PHONE_IP

# Check if connected
if ! adb devices | grep -q "$PHONE_IP"; then
    echo "Error: Could not connect to device at $PHONE_IP"
    echo "Make sure USB debugging is enabled and the device is on the same network"
    exit 1
fi

# Build the debug APK
echo "Building debug APK with mock data..."
./gradlew assembleDebug

if [ ! -f "$APK_PATH" ]; then
    echo "Error: APK not found at $APK_PATH"
    echo "Build may have failed"
    exit 1
fi

# Install the APK
echo "Installing APK to device..."
adb -s $PHONE_IP install -r $APK_PATH

if [ $? -eq 0 ]; then
    echo "Installation successful!"
    echo ""
    echo "The app has been installed with mock data for debugging."
    echo "This avoids copying the large Perseus dataset to the device."
    echo ""
    echo "To launch the app:"
    echo "  adb -s $PHONE_IP shell am start -n com.perseus.viewer.debug/com.perseus.viewer.MainActivity"
else
    echo "Installation failed!"
    exit 1
fi