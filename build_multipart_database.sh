#!/bin/bash
# Build script for multi-part database deployment

set -e

echo "Building multi-part database for Play Asset Delivery..."

# Step 1: Build the database
echo "Step 1: Building database..."
cd data-prep
python3 create_perseus_database.py
cd ..

# Step 2: Split the compressed database
echo "Step 2: Splitting compressed database..."
cd data-prep
if [ -f "../perseus_database/src/main/assets/perseus_texts.db.zip" ]; then
    # Create output directory for parts
    mkdir -p split_output
    
    # Split the database (450MB chunks to stay under 512MB limit)
    python3 split_database_for_assets.py split ../perseus_database/src/main/assets/perseus_texts.db.zip 450 split_output
    
    # Verify the split
    python3 split_database_for_assets.py verify split_output/perseus_texts.db.manifest.json
else
    echo "Error: Compressed database not found!"
    exit 1
fi
cd ..

# Step 3: Create asset pack modules
echo "Step 3: Creating asset pack modules..."

# Function to create an asset pack module
create_asset_pack() {
    local pack_number=$1
    local part_file=$2
    local pack_name="perseus_database_part${pack_number}"
    
    echo "Creating asset pack: $pack_name"
    
    # Create module directory structure
    mkdir -p "${pack_name}/src/main/assets"
    
    # Copy the part file
    cp "$part_file" "${pack_name}/src/main/assets/"
    
    # Copy manifest to first pack
    if [ $pack_number -eq 1 ]; then
        cp "data-prep/split_output/perseus_texts.db.manifest.json" "${pack_name}/src/main/assets/"
    fi
    
    # Create build.gradle for the module
    cat > "${pack_name}/build.gradle" << EOF
plugins {
    id 'com.android.asset-pack'
}

assetPack {
    packName = "${pack_name}"
    dynamicDelivery {
        deliveryType = "fast-follow"
    }
}
EOF

    # Create AndroidManifest.xml
    mkdir -p "${pack_name}/src/main"
    cat > "${pack_name}/src/main/AndroidManifest.xml" << EOF
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:dist="http://schemas.android.com/apk/distribution"
    package="com.classicsviewer.app.${pack_name}">
    
    <dist:module dist:type="asset-pack">
        <dist:fusing dist:include="false" />
        <dist:delivery>
            <dist:fast-follow />
        </dist:delivery>
    </dist:module>
</manifest>
EOF
}

# Process each part file
part_number=1
for part_file in data-prep/split_output/perseus_texts.db.part*; do
    if [[ "$part_file" == *.manifest.json ]]; then
        continue
    fi
    create_asset_pack $part_number "$part_file"
    ((part_number++))
done

# Step 4: Update settings.gradle to include new modules
echo "Step 4: Updating settings.gradle..."

# Read current settings
current_settings=$(cat settings.gradle)

# Add new asset pack modules if not already present
for ((i=1; i<part_number; i++)); do
    module_name="perseus_database_part${i}"
    if ! grep -q "$module_name" settings.gradle; then
        echo "include ':$module_name'" >> settings.gradle
    fi
done

# Step 5: Update app/build.gradle to reference asset packs
echo "Step 5: Updating app/build.gradle..."

# Create a backup
cp app/build.gradle app/build.gradle.backup

# Generate asset pack references
asset_packs=""
for ((i=1; i<part_number; i++)); do
    if [ $i -gt 1 ]; then
        asset_packs+=", "
    fi
    asset_packs+="':perseus_database_part${i}'"
done

# Update build.gradle (you may need to adjust this based on your exact gradle file)
echo ""
echo "Add the following to your app/build.gradle android block:"
echo "assetPacks = [$asset_packs]"
echo ""

echo "Build complete!"
echo "Total parts created: $((part_number-1))"
echo ""
echo "Next steps:"
echo "1. Remove the old single perseus_database module from settings.gradle"
echo "2. Add assetPacks = [$asset_packs] to app/build.gradle"
echo "3. Update your app code to use MultiPartAssetPackDatabaseHelper"
echo "4. Build and deploy with: ./gradlew bundleRelease"