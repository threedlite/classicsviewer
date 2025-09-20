#!/bin/bash
# Script to split the extended ZIM file into 1.5GB chunks
# This is necessary for distribution and storage limitations

set -e  # Exit on error

ZIM_FILE="classicsviewer_extended.zim"
CHUNK_SIZE="1500M"  # 1.5GB chunks
PREFIX="classicsviewer_extended.zim.part"

echo "============================================"
echo "    SPLITTING EXTENDED ZIM FILE            "
echo "============================================"
echo ""

# Check if ZIM file exists
if [ ! -f "$ZIM_FILE" ]; then
    echo "❌ ERROR: $ZIM_FILE not found!"
    echo "Please build the extended ZIM first using ./build_extended_clean.sh"
    exit 1
fi

# Get file size
SIZE=$(ls -lh "$ZIM_FILE" | awk '{print $5}')
echo "📁 Input file: $ZIM_FILE"
echo "📏 File size: $SIZE"
echo ""

# Remove any existing part files
echo "🧹 Cleaning up old part files..."
rm -f ${PREFIX}*
echo ""

# Split the file
echo "✂️  Splitting into ${CHUNK_SIZE} chunks..."
split -b "$CHUNK_SIZE" -d "$ZIM_FILE" "$PREFIX"
echo ""

# Rename parts with proper numbering (01, 02, etc.)
echo "📝 Renaming part files..."
# First, rename to temporary names to avoid overwriting
for file in ${PREFIX}[0-9][0-9]; do
    if [ -f "$file" ]; then
        mv "$file" "${file}.tmp"
    fi
done
# Now rename from temporary names to final names (starting from 01)
PART_NUM=1
for file in ${PREFIX}[0-9][0-9].tmp; do
    if [ -f "$file" ]; then
        NEW_NAME=$(printf "%s%02d" "$PREFIX" "$PART_NUM")
        mv "$file" "$NEW_NAME"
        SIZE=$(ls -lh "$NEW_NAME" | awk '{print $5}')
        echo "  ✓ $NEW_NAME ($SIZE)"
        PART_NUM=$((PART_NUM + 1))
    fi
done
echo ""

# Create a README for reconstruction
README_FILE="${PREFIX}00.readme"
echo "📄 Creating reconstruction instructions..."
cat > "$README_FILE" << EOF
Extended ZIM Reconstruction Instructions
=========================================

To reconstruct the original classicsviewer_extended.zim file:

Linux/macOS:
  cat classicsviewer_extended.zim.part* > classicsviewer_extended.zim

Windows (PowerShell):
  Get-Content classicsviewer_extended.zim.part* -ReadCount 0 -Encoding Byte | Set-Content classicsviewer_extended.zim -Encoding Byte

Verification:
  After reconstruction, verify the file integrity by opening it in Kiwix.

File parts:
EOF

# Add file list to README
for file in ${PREFIX}[0-9][0-9]; do
    if [ -f "$file" ]; then
        SIZE=$(ls -lh "$file" | awk '{print $5}')
        echo "  - $(basename $file) ($SIZE)" >> "$README_FILE"
    fi
done

echo "  ✓ Created $README_FILE"
echo ""

# Summary
TOTAL_PARTS=$(ls -1 ${PREFIX}[0-9][0-9] 2>/dev/null | wc -l | tr -d ' ')
echo "============================================"
echo "✅ SPLIT COMPLETE!"
echo "📦 Created $TOTAL_PARTS part files"
echo "📝 Reconstruction instructions in $README_FILE"
echo ""
echo "To reconstruct:"
echo "  cat ${PREFIX}* > $ZIM_FILE"
echo "============================================"