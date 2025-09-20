#!/bin/bash

# Script to package Homer Iliad audio files for Classics Viewer app
# Usage: ./package_audio.sh [output_name]
# Default output: homer_iliad_chamberlain_audio.zip

SOURCE_DIR="homer_iliad_chamberlain_audio"
OUTPUT_NAME="${1:-homer_iliad_chamberlain_audio.zip}"

echo "========================================="
echo "Creating Audio Package: $OUTPUT_NAME"
echo "========================================="

# Check source directory
if [ ! -d "$SOURCE_DIR/Homer/Iliad" ]; then
    echo "Error: $SOURCE_DIR/Homer/Iliad not found!"
    exit 1
fi

# Count files
cd "$SOURCE_DIR"
total_files=$(find Homer/Iliad -name "*.mp4" 2>/dev/null | wc -l)
echo "Found $total_files MP4 files"

# Remove old ZIP if exists
cd ..
[ -f "$OUTPUT_NAME" ] && rm "$OUTPUT_NAME"

# Create ZIP (Homer must be at root of ZIP)
echo "Creating ZIP package..."
cd "$SOURCE_DIR"
zip -r "../$OUTPUT_NAME" Homer
cd ..

# Verify
if [ -f "$OUTPUT_NAME" ]; then
    size=$(ls -lh "$OUTPUT_NAME" | awk '{print $5}')
    echo "✓ Created $OUTPUT_NAME ($size)"
    echo ""
    echo "To push to phone:"
    echo "adb push $OUTPUT_NAME /sdcard/Download/"
else
    echo "Error: Failed to create ZIP!"
    exit 1
fi