#!/bin/bash

# Generate iOS app icons from the Android Play Store icon
# Source image
SOURCE="/Users/user1/git/classicsviewer/play-store-assets/play_store_icon.png"
DEST_DIR="/Users/user1/git/classicsviewer/ios/ClassicsViewer/Assets.xcassets/AppIcon.appiconset"

# Check if source exists
if [ ! -f "$SOURCE" ]; then
    echo "Source icon not found: $SOURCE"
    exit 1
fi

echo "Generating iOS app icons..."

# iPhone icons
sips -z 40 40 "$SOURCE" --out "$DEST_DIR/Icon-20@2x.png" > /dev/null 2>&1
sips -z 60 60 "$SOURCE" --out "$DEST_DIR/Icon-20@3x.png" > /dev/null 2>&1
sips -z 58 58 "$SOURCE" --out "$DEST_DIR/Icon-29@2x.png" > /dev/null 2>&1
sips -z 87 87 "$SOURCE" --out "$DEST_DIR/Icon-29@3x.png" > /dev/null 2>&1
sips -z 80 80 "$SOURCE" --out "$DEST_DIR/Icon-40@2x.png" > /dev/null 2>&1
sips -z 120 120 "$SOURCE" --out "$DEST_DIR/Icon-40@3x.png" > /dev/null 2>&1
sips -z 120 120 "$SOURCE" --out "$DEST_DIR/Icon-60@2x.png" > /dev/null 2>&1
sips -z 180 180 "$SOURCE" --out "$DEST_DIR/Icon-60@3x.png" > /dev/null 2>&1

# iPad icons
sips -z 20 20 "$SOURCE" --out "$DEST_DIR/Icon-20.png" > /dev/null 2>&1
sips -z 40 40 "$SOURCE" --out "$DEST_DIR/Icon-20@2x-1.png" > /dev/null 2>&1
sips -z 29 29 "$SOURCE" --out "$DEST_DIR/Icon-29.png" > /dev/null 2>&1
sips -z 58 58 "$SOURCE" --out "$DEST_DIR/Icon-29@2x-1.png" > /dev/null 2>&1
sips -z 40 40 "$SOURCE" --out "$DEST_DIR/Icon-40.png" > /dev/null 2>&1
sips -z 80 80 "$SOURCE" --out "$DEST_DIR/Icon-40@2x-1.png" > /dev/null 2>&1
sips -z 76 76 "$SOURCE" --out "$DEST_DIR/Icon-76.png" > /dev/null 2>&1
sips -z 152 152 "$SOURCE" --out "$DEST_DIR/Icon-76@2x.png" > /dev/null 2>&1
sips -z 167 167 "$SOURCE" --out "$DEST_DIR/Icon-83.5@2x.png" > /dev/null 2>&1

# App Store icon
sips -z 1024 1024 "$SOURCE" --out "$DEST_DIR/Icon-1024.png" > /dev/null 2>&1

echo "iOS app icons generated successfully!"
echo "Generated icons in: $DEST_DIR"
ls -la "$DEST_DIR"/*.png | wc -l
echo "icons created"