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
# Build sample database for deployment (this goes to Play Store)
# This also creates the ZIP files in app/src/debug/assets and app/src/main/assets
python3 create_perseus_database.py sample
echo "✅ Sample database rebuilt successfully"
cd ..

# Step 2 and 3 are no longer needed - database creation script handles everything
echo "📦 Database ZIP files already created by database creation script"

# Step 4: Verify ZIP integrity
echo "🔍 Step 4: Verifying ZIP integrity..."
if unzip -t app/src/debug/assets/perseus_texts.db.zip > /dev/null 2>&1; then
    echo "✅ ZIP file is valid"
else
    echo "❌ ZIP file is corrupted - aborting"
    exit 1
fi

# Step 5: Database already in correct location
echo "✅ Step 5: Database is in app/src/debug/assets/"
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