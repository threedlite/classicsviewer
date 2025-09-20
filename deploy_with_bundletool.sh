#!/bin/bash

# Exit on any error
set -e

echo "=== Building and deploying with Play Asset Delivery ==="

# 1. Build the database and copy to asset pack
echo "Skipping database build (already exists)..."
# cd data-prep
# python3 create_perseus_database.py
# cd ..

# 2. Build the AAB
echo "Building Android App Bundle..."
./gradlew bundleDebug

# 3. Generate APKs with bundletool
echo "Generating APKs with bundletool..."
rm -f output.apks
java -jar dev-util/bundletool-all.jar build-apks \
    --bundle=app/build/outputs/bundle/debug/app-debug.aab \
    --output=output.apks \
    --local-testing \
    --connected-device

# 4. Install on device
echo "Installing on device..."
java -jar dev-util/bundletool-all.jar install-apks --apks=output.apks

# 5. Clear app data to force language selection
echo "Clearing app data..."
adb shell pm clear com.classicsviewer.app.debug

echo "=== Deployment complete! ==="
echo "The app should now start with language selection."