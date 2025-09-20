#!/bin/bash
# Clean build script for full ZIM
# This script ensures a clean, reproducible build

set -e  # Exit on error

echo "============================================"
echo "    FULL ZIM BUILD (128 authors)           "
echo "============================================"
echo ""

# Step 1: Clean environment
echo "[1/5] Cleaning environment..."
killall python3 2>/dev/null || true
killall Python 2>/dev/null || true
rm -f /tmp/*.lock
rm -rf zim_content_optimized
echo "✓ Environment cleaned"
echo ""

# Step 2: Activate virtual environment
echo "[2/5] Activating Python environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Step 3: Generate content
echo "[3/5] Generating HTML content..."
echo "This takes about 90-120 seconds..."
python3 create_zim_content_optimized.py
echo "✓ Content generation complete"
echo ""

# Step 4: Count generated files
FILE_COUNT=$(find zim_content_optimized -name "*.html" | wc -l | tr -d ' ')
echo "[4/5] Generated $FILE_COUNT HTML files"
echo ""

# Step 5: Create ZIM file
echo "[5/5] Creating ZIM archive..."
echo "This takes about 30-40 minutes..."
python3 create_zim_optimized.py --output classicsviewer_full.zim
echo ""

# Final verification
if [ -f "classicsviewer_full.zim" ]; then
    SIZE=$(ls -lh classicsviewer_full.zim | awk '{print $5}')
    echo "============================================"
    echo "✓ BUILD SUCCESSFUL!"
    echo "File: classicsviewer_full.zim"
    echo "Size: $SIZE"
    echo ""
    echo "Test with:"
    echo "  open -a Kiwix classicsviewer_full.zim"
    echo "  or"
    echo "  kiwix-serve --port 8080 classicsviewer_full.zim"
    echo "============================================"
else
    echo "❌ ERROR: ZIM file not created"
    exit 1
fi