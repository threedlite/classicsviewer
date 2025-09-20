#!/bin/bash

# OBB Creation Script for Classics Viewer

VERSION_CODE=1
PACKAGE_NAME="com.classicsviewer.app"
DB_PATH="data-prep/perseus_texts.db"

echo "Creating OBB file for Classics Viewer..."

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    echo "Please run: cd data-prep && python3 create_database_from_perseus.py"
    exit 1
fi

# Create OBB filename
OBB_NAME="main.$VERSION_CODE.$PACKAGE_NAME.obb"

# Create OBB (compressed ZIP to reduce download size)
echo "Packaging database into OBB..."
cd data-prep
# Use -9 for maximum compression
zip -9 "../$OBB_NAME" perseus_texts.db
cd ..

# Show OBB info
if [ -f "$OBB_NAME" ]; then
    echo "✓ OBB created successfully: $OBB_NAME"
    echo "  Size: $(du -h "$OBB_NAME" | cut -f1)"
    echo ""
    echo "To install on device:"
    echo "  1. Connect device via USB"
    echo "  2. Run: adb push $OBB_NAME /sdcard/Android/obb/$PACKAGE_NAME/"
    echo ""
    echo "Or manually copy to:"
    echo "  /Android/obb/$PACKAGE_NAME/$OBB_NAME"
else
    echo "Error: Failed to create OBB file"
    exit 1
fi