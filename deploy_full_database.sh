#!/bin/bash

# Deployment script for full database - for local debugging

set -e

echo "=== FULL DATABASE BUILD AND DEPLOYMENT ==="
echo "⚠️  This will take ~4 minutes to rebuild the database"
echo ""

# Step 1: Rebuild full database
echo "🔨 Step 1: Rebuilding full database..."
cd data-prep
python3 create_perseus_database.py full
echo "✅ Full database rebuilt successfully"
cd ..

# Step 2: Extract the compressed full database
echo "📦 Step 2: Extracting full database for deployment..."
cd data-prep
if [ -f "perseus_texts_full.db.zip" ]; then
    # Create temporary copy for deployment
    unzip -o perseus_texts_full.db.zip
    
    # Copy to asset pack location with standard name
    mkdir -p ../perseus_database/src/main/assets
    zip -9 ../perseus_database/src/main/assets/perseus_texts.db.zip perseus_texts_full.db
    
    # Clean up extracted file
    rm -f perseus_texts_full.db
    echo "✅ Full database prepared for deployment"
else
    echo "❌ Full database ZIP not found - aborting"
    exit 1
fi
cd ..

# Step 3: Verify ZIP integrity
echo "🔍 Step 3: Verifying ZIP integrity..."
if unzip -t perseus_database/src/main/assets/perseus_texts.db.zip > /dev/null 2>&1; then
    echo "✅ ZIP file is valid"
else
    echo "❌ ZIP file is corrupted - aborting"
    exit 1
fi

# Step 4: Copy to debug assets for local testing
echo "📋 Step 4: Copying to debug assets..."
mkdir -p app/src/debug/assets
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/
echo "✅ Database copied to debug assets"

# Step 5: Build and install debug APK
echo "🔧 Step 5: Building and installing debug APK..."
./gradlew installDebug
echo "✅ APK installed successfully"

# Step 6: Clear app data for fresh start
echo "🧹 Step 6: Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug
echo "✅ App data cleared"

echo ""
echo "=== FULL DATABASE DEPLOYMENT COMPLETE! ==="
echo "✅ Full database deployed for local debugging"
echo "✅ App will extract database on first launch (~6-7 seconds)"
echo ""
echo "🚀 Launch the app now to test"