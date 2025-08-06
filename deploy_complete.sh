#!/bin/bash

# Complete deployment script - rebuilds everything from scratch
# Use this after any schema changes or when in doubt

set -e

echo "=== COMPLETE REBUILD AND DEPLOYMENT ==="
echo "⚠️  This will take ~4 minutes to rebuild the database"
echo ""

# Step 1: Rebuild database from scratch
echo "🔨 Step 1: Rebuilding database from scratch..."
cd data-prep
python3 create_perseus_database.py
echo "✅ Database rebuilt successfully"
cd ..

# Step 2: Remove old compressed databases
echo "🗑️  Step 2: Removing old compressed databases..."
rm -f perseus_database/src/main/assets/perseus_texts.db.zip
rm -f app/src/debug/assets/perseus_texts.db.zip
echo "✅ Old compressed databases removed"

# Step 3: Create fresh compressed database
echo "📦 Step 3: Creating fresh compressed database..."
cd data-prep
zip -9 ../perseus_database/src/main/assets/perseus_texts.db.zip perseus_texts.db
cd ..

# Step 4: Verify ZIP integrity
echo "🔍 Step 4: Verifying ZIP integrity..."
if unzip -t perseus_database/src/main/assets/perseus_texts.db.zip > /dev/null 2>&1; then
    echo "✅ ZIP file is valid"
else
    echo "❌ ZIP file is corrupted - aborting"
    exit 1
fi

# Step 5: Copy to debug assets for local testing
echo "📋 Step 5: Copying to debug assets..."
mkdir -p app/src/debug/assets
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/
echo "✅ Database copied to debug assets"

# Step 6: Build and install debug APK
echo "🔧 Step 6: Building and installing debug APK..."
./gradlew installDebug
echo "✅ APK installed successfully"

# Step 7: Clear app data for fresh start
echo "🧹 Step 7: Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug
echo "✅ App data cleared"

echo ""
echo "=== DEPLOYMENT COMPLETE! ==="
echo "✅ Database rebuilt from scratch"
echo "✅ Schema should now match exactly"
echo "✅ App will extract database on first launch (~6-7 seconds)"
echo ""
echo "🚀 Launch the app now to test"