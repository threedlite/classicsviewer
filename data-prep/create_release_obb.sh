#!/bin/bash

# Create release OBB file (without .debug suffix)

set -e

cd output

# Check if the debug OBB exists
if [ ! -f "main.1.com.classicsviewer.app.debug.obb" ]; then
    echo "Error: Debug OBB not found. Please build it first."
    exit 1
fi

# Create release OBB by copying the debug one
echo "Creating release OBB..."
cp main.1.com.classicsviewer.app.debug.obb main.1.com.classicsviewer.app.obb

echo "Release OBB created: main.1.com.classicsviewer.app.obb"
echo "Size: $(du -h main.1.com.classicsviewer.app.obb | cut -f1)"
echo ""
echo "This OBB file should be uploaded as an expansion file in Google Play Console"