#!/bin/bash
# Optimized build and deploy script that doesn't include database in APK

echo "=== Optimized Classics Viewer Build & Deploy ==="
echo

# Clean any old database files from assets
echo "Cleaning old database files from assets..."
find app/src -name "*.db" -type f -delete
echo

# Build the app (without database in assets)
echo "Building APK (database will be loaded from OBB only)..."
./gradlew clean assembleDebug

if [ $? -ne 0 ]; then
    echo "Error: Build failed!"
    exit 1
fi

# Find the APK
APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
    echo "Error: APK not found at $APK_PATH"
    exit 1
fi

echo "✓ APK built successfully: $(du -h $APK_PATH | cut -f1)"
echo

# Check for connected device
if ! adb devices | grep -q "device$"; then
    echo "Error: No Android device connected"
    exit 1
fi

echo "Device connected:"
adb devices | grep device$ | head -1
echo

# Uninstall old version
echo "Uninstalling old version..."
adb uninstall com.classicsviewer.app.debug 2>/dev/null

# Install new APK
echo "Installing APK..."
adb install -r "$APK_PATH"

# Check if OBB exists on device
echo
echo "Checking for OBB on device..."
OBB_EXISTS=$(adb shell "[ -f /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/main.1.com.classicsviewer.app.debug.obb ] && echo 'yes' || echo 'no'")

if [ "$OBB_EXISTS" = "no" ]; then
    echo "⚠️  OBB not found on device. Deploying database..."
    
    # Check if we have the database
    if [ ! -f "data-prep/perseus_texts.db" ]; then
        echo "Error: Database not found at data-prep/perseus_texts.db"
        exit 1
    fi
    
    # Create compressed OBB
    echo "Creating compressed OBB file..."
    cd data-prep
    zip -9 ../main.1.com.classicsviewer.app.debug.obb perseus_texts.db
    cd ..
    echo "Compressed OBB size: $(du -h main.1.com.classicsviewer.app.debug.obb | cut -f1)"
    
    # Push to device
    echo "Pushing OBB to device..."
    adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
    adb push main.1.com.classicsviewer.app.debug.obb /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
    
    # Clean up
    rm -f main.1.com.classicsviewer.app.debug.obb
    echo "✓ OBB deployed"
else
    echo "✓ OBB already exists on device"
fi

# Launch app
echo
echo "Launching app..."
adb shell am start -n com.classicsviewer.app.debug/com.classicsviewer.app.MainActivity

echo
echo "=== Deployment Complete ==="
echo
echo "APK size: $(du -h $APK_PATH | cut -f1) (no database included)"
echo "Database location: /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/"
echo
echo "The app will now:"
echo "1. Load database from OBB only (no assets fallback)"
echo "2. Show error if OBB is missing"
echo "3. Use less memory during builds"
echo
echo "To monitor logs:"
echo "adb logcat | grep -E 'PerseusDatabase|ObbDatabaseHelper|PerseusRepository|TextViewerPager'"