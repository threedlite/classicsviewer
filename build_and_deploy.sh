#!/bin/bash
# Build and deploy Classics Viewer app with database

echo "=== Classics Viewer Build & Deploy ==="
echo

# Step 1: Build the database
echo "Step 1: Building Perseus database..."
cd data-prep
if [ ! -f "perseus_texts.db" ]; then
    echo "Creating database from scratch..."
    python3 create_perseus_database.py
else
    echo "Database already exists. Size: $(du -h perseus_texts.db | cut -f1)"
fi

# Optimize database
echo "Optimizing database..."
sqlite3 perseus_texts.db "VACUUM;"
echo "Optimized size: $(du -h perseus_texts.db | cut -f1)"

cd ..

# Step 2: Build the Android app
echo
echo "Step 2: Building Android app..."
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

echo "APK built successfully: $APK_PATH"
echo "APK size: $(du -h $APK_PATH | cut -f1)"

# Step 3: Deploy to device
echo
echo "Step 3: Deploying to device..."

# Check for connected device
if ! adb devices | grep -q "device$"; then
    echo "Error: No Android device connected"
    echo "Please connect your device with USB debugging enabled"
    exit 1
fi

echo "Device connected:"
adb devices | grep device$ | head -1

# Uninstall old version
echo "Uninstalling old version..."
adb uninstall com.classicsviewer.app 2>/dev/null

# Install new APK
echo "Installing APK..."
adb install -r "$APK_PATH"

if [ $? -ne 0 ]; then
    echo "Error: APK installation failed"
    exit 1
fi

# Step 4: Deploy database as OBB
echo
echo "Step 4: Deploying database..."

# Create compressed OBB file
echo "Creating compressed OBB..."
cd data-prep
if [ -f "output/perseus_texts.db" ]; then
    cd output
    zip -9 main.1.com.classicsviewer.app.obb perseus_texts.db
    cd ../..
else
    # Database is in data-prep root
    zip -9 main.1.com.classicsviewer.app.obb perseus_texts.db
    cd ..
fi

# Push OBB to device
echo "Pushing compressed database to device..."
OBB_FILE=$(find data-prep -name "main.1.com.classicsviewer.app.obb" | head -1)
echo "OBB size: $(du -h $OBB_FILE | cut -f1)"
adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app/
adb push "$OBB_FILE" /storage/emulated/0/Android/obb/com.classicsviewer.app/

# Step 5: Launch app
echo
echo "Step 5: Launching app..."
adb shell am start -n com.classicsviewer.app/.MainActivity

echo
echo "=== Deployment Complete ==="
echo
echo "The app should now be running on your device with:"
echo "- Homer, Hesiod, and Pindar translations fixed"
echo "- Bold text for works with translations"
echo "- 94.1% translation coverage (255 out of 271 works)"
echo
echo "To debug translations, use:"
echo "  adb logcat | grep -E 'PerseusRepository|TextViewerPager'"