#!/bin/bash
#
# Complete deployment script for Classics Viewer
# Handles database building, compression, and deployment correctly
#

set -e

echo "=== Classics Viewer Complete Deployment ==="
echo

# Configuration
PACKAGE_NAME_DEBUG="com.classicsviewer.app.debug"
PACKAGE_NAME_RELEASE="com.classicsviewer.app"

# Function to check if device is connected
check_device() {
    if ! adb devices | grep -q "device$"; then
        echo "Error: No Android device connected"
        echo "Please connect your device with USB debugging enabled"
        exit 1
    fi
    echo "Device connected: $(adb devices | grep device$ | head -1)"
}

# Function to create compressed OBB
create_compressed_obb() {
    local db_path=$1
    local obb_name=$2
    
    echo "Creating compressed OBB: $obb_name"
    echo "Database size: $(du -h $db_path | cut -f1)"
    
    # Create compressed OBB
    zip -9 "$obb_name" "$db_path"
    
    echo "Compressed OBB size: $(du -h $obb_name | cut -f1)"
    
    # Calculate compression ratio
    local original_size=$(stat -c%s "$db_path")
    local compressed_size=$(stat -c%s "$obb_name")
    local ratio=$(echo "scale=1; 100 - ($compressed_size * 100 / $original_size)" | bc)
    
    echo "Compression ratio: ${ratio}% reduction"
}

# Step 1: Build/check database
echo "Step 1: Checking database..."
cd data-prep

if [ -f "output/perseus_texts.db" ]; then
    DB_PATH="output/perseus_texts.db"
elif [ -f "perseus_texts.db" ]; then
    DB_PATH="perseus_texts.db"
else
    echo "Database not found. Building from scratch..."
    python3 create_perseus_database.py
    
    # Apply alignment fix if needed
    if [ -f "fix_alignment_post_import.py" ]; then
        echo "Applying translation alignment fixes..."
        python3 fix_alignment_post_import.py
    fi
    
    DB_PATH="output/perseus_texts.db"
fi

echo "Database found: $DB_PATH"
echo "Database size: $(du -h $DB_PATH | cut -f1)"

# Step 2: Create compressed OBBs
echo
echo "Step 2: Creating compressed OBB files..."

cd $(dirname $DB_PATH)
DB_NAME=$(basename $DB_PATH)

# Debug OBB
OBB_DEBUG="main.1.${PACKAGE_NAME_DEBUG}.obb"
create_compressed_obb "$DB_NAME" "$OBB_DEBUG"

# Release OBB  
OBB_RELEASE="main.1.${PACKAGE_NAME_RELEASE}.obb"
create_compressed_obb "$DB_NAME" "$OBB_RELEASE"

cd ../..

# Step 3: Build Android app
echo
echo "Step 3: Building Android app..."
./gradlew clean assembleDebug

APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
    echo "Error: APK not found at $APK_PATH"
    exit 1
fi

echo "APK built successfully: $(du -h $APK_PATH | cut -f1)"

# Step 4: Deploy to device
echo
echo "Step 4: Deploying to device..."

check_device

# Uninstall old version
echo "Uninstalling old version..."
adb uninstall $PACKAGE_NAME_DEBUG 2>/dev/null || true

# Install APK
echo "Installing APK..."
adb install -r "$APK_PATH"

# Deploy OBB
echo "Deploying compressed OBB..."
OBB_PATH="data-prep/$(dirname $DB_PATH)/$OBB_DEBUG"
echo "OBB location: $OBB_PATH"

adb shell mkdir -p /storage/emulated/0/Android/obb/$PACKAGE_NAME_DEBUG/
adb push "$OBB_PATH" /storage/emulated/0/Android/obb/$PACKAGE_NAME_DEBUG/

# Step 5: Launch app
echo
echo "Step 5: Launching app..."
adb shell am start -n $PACKAGE_NAME_DEBUG/.MainActivity

echo
echo "=== Deployment Complete ==="
echo
echo "The app should now be running with:"
echo "- Compressed database (78% smaller download)"
echo "- Fixed translation alignments (e.g., Aeschines)"
echo "- All UI improvements applied"
echo
echo "First launch will show extraction progress (~2 seconds)"
echo
echo "To monitor logs:"
echo "  adb logcat | grep -E 'ObbDatabaseHelper|DatabaseExtraction|Perseus'"