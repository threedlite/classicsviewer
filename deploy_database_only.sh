#!/bin/bash
# Deploy just the database to test with existing app

echo "=== Database Deployment ==="
echo

# Check if database exists
if [ ! -f "data-prep/perseus_texts.db" ]; then
    echo "Error: Database not found at data-prep/perseus_texts.db"
    echo "Run 'cd data-prep && python3 create_perseus_database.py' first"
    exit 1
fi

# Show database info
echo "Database info:"
ls -lh data-prep/perseus_texts.db
echo

# Check for connected device
if ! adb devices | grep -q "device$"; then
    echo "Error: No Android device connected"
    echo "Please connect your device with USB debugging enabled"
    exit 1
fi

echo "Device connected:"
adb devices | grep device$ | head -1
echo

# Create compressed OBB file
echo "Creating compressed OBB file..."
cd data-prep
zip -9 ../main.1.com.classicsviewer.app.obb perseus_texts.db
cd ..
echo "Compressed OBB size: $(du -h main.1.com.classicsviewer.app.obb | cut -f1)"

# Push to device
echo "Pushing database to device..."
adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app/
adb push main.1.com.classicsviewer.app.obb /storage/emulated/0/Android/obb/com.classicsviewer.app/

# Also push to Download for backup
echo
echo "Also copying to Downloads folder..."
adb push data-prep/perseus_texts.db /storage/emulated/0/Download/

# Clean up
rm -f main.1.com.classicsviewer.app.obb

echo
echo "=== Database Deployed ==="
echo
echo "Database locations:"
echo "1. OBB: /storage/emulated/0/Android/obb/com.classicsviewer.app/main.1.com.classicsviewer.app.obb"
echo "2. Download: /storage/emulated/0/Download/perseus_texts.db"
echo
echo "Next steps:"
echo "1. Clear app data: Settings → Apps → Classics Viewer → Clear Data"
echo "2. Launch the app"
echo "3. Check if Homer/Hesiod/Pindar show translations"
echo
echo "To verify database on device:"
echo "adb shell sqlite3 /storage/emulated/0/Download/perseus_texts.db \"SELECT COUNT(*) FROM translation_segments WHERE book_id LIKE 'tlg0012%';\""