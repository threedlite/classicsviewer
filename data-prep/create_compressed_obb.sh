#!/bin/bash

# This script creates a compressed OBB file from the Perseus database

set -e

# Configuration
DB_FILE="output/perseus_texts.db"
OBB_DIR="output"
OBB_NAME_DEBUG="main.1.com.classicsviewer.app.debug.obb"
OBB_NAME_RELEASE="main.1.com.classicsviewer.app.obb"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file $DB_FILE not found!"
    echo "Please run the build scripts first to create the database."
    exit 1
fi

# Show original database size
echo "Original database size: $(du -h $DB_FILE | cut -f1)"

# Create compressed OBB files
echo "Creating compressed OBB files..."

# Debug version
echo -n "Creating debug OBB... "
cd output
zip -9 "$OBB_NAME_DEBUG" perseus_texts.db
echo "done"

# Release version  
echo -n "Creating release OBB... "
zip -9 "$OBB_NAME_RELEASE" perseus_texts.db
echo "done"

cd ..

# Show compressed sizes
echo
echo "Compressed OBB sizes:"
echo "Debug:   $(du -h output/$OBB_NAME_DEBUG | cut -f1)"
echo "Release: $(du -h output/$OBB_NAME_RELEASE | cut -f1)"

# Calculate compression ratio
ORIGINAL_SIZE=$(stat -c%s "$DB_FILE")
COMPRESSED_SIZE=$(stat -c%s "output/$OBB_NAME_DEBUG")
RATIO=$(echo "scale=2; 100 - ($COMPRESSED_SIZE * 100 / $ORIGINAL_SIZE)" | bc)

echo
echo "Compression ratio: ${RATIO}% reduction"
echo
echo "OBB files created in output/"
echo "Deploy with: adb push output/$OBB_NAME_DEBUG /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/"