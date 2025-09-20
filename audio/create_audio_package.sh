#!/bin/bash

# Script to create audio packages for Classics Viewer
# The ZIP must have the correct structure: Homer/Iliad/book_N/line_X.mp4

# Check if audio directory exists
if [ ! -d "homer_iliad_chamberlain_audio" ]; then
    echo "Error: homer_iliad_chamberlain_audio directory not found!"
    echo "Please ensure the audio files are in the correct directory structure."
    exit 1
fi

echo "Creating Homer Iliad Chamberlain audio package..."

# Remove old ZIP if it exists
if [ -f "homer_iliad_chamberlain_audio.zip" ]; then
    echo "Removing old ZIP file..."
    rm homer_iliad_chamberlain_audio.zip
fi

# Create the ZIP with the correct structure
# The app expects: Homer/Iliad/book_N/line_X.mp4
# So we need to go into the directory and zip from there
cd homer_iliad_chamberlain_audio

# Count total files for verification
total_files=$(find Homer/Iliad -name "*.mp4" 2>/dev/null | wc -l)
echo "Found $total_files MP4 files to package"

if [ $total_files -eq 0 ]; then
    echo "Error: No MP4 files found in Homer/Iliad directory!"
    exit 1
fi

# Create ZIP with Homer directory at the root
echo "Creating ZIP package..."
zip -r ../homer_iliad_chamberlain_audio.zip Homer

cd ..

# Verify the ZIP was created and show info
if [ -f "homer_iliad_chamberlain_audio.zip" ]; then
    size=$(ls -lh homer_iliad_chamberlain_audio.zip | awk '{print $5}')
    echo "✓ Successfully created homer_iliad_chamberlain_audio.zip ($size)"
    
    # Show structure verification
    echo ""
    echo "Verifying package structure (first 10 files):"
    unzip -l homer_iliad_chamberlain_audio.zip | head -20
    
    # Count files in ZIP
    zip_files=$(unzip -l homer_iliad_chamberlain_audio.zip | grep "\.mp4" | wc -l)
    echo ""
    echo "Total files in ZIP: $zip_files"
    
    if [ $zip_files -ne $total_files ]; then
        echo "Warning: File count mismatch! Original: $total_files, ZIP: $zip_files"
    fi
else
    echo "Error: Failed to create ZIP file!"
    exit 1
fi

echo ""
echo "To push to phone, run:"
echo "adb push homer_iliad_chamberlain_audio.zip /sdcard/Download/"