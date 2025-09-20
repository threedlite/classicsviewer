#!/bin/bash
# Clean build script for sample ZIM
# This script ensures a clean, reproducible build

set -e  # Exit on error

echo "============================================"
echo "    SAMPLE ZIM BUILD (12 authors)          "
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
echo "This takes about 70-90 seconds..."
python3 create_zim_content_optimized.py --sample
echo "✓ Content generation complete"
echo ""

# Step 4: Count generated files
FILE_COUNT=$(find zim_content_optimized -name "*.html" | wc -l | tr -d ' ')
echo "[4/5] Generated $FILE_COUNT HTML files"
echo ""

# Step 5: Create ZIM file
echo "[5/5] Creating ZIM archive..."
echo "This takes about 7-8 minutes..."
python3 create_zim_optimized.py --output classicsviewer_sample.zim
echo ""

# Final verification
if [ -f "classicsviewer_sample.zim" ]; then
    SIZE=$(ls -lh classicsviewer_sample.zim | awk '{print $5}')
    echo "============================================"
    echo "✓ BUILD SUCCESSFUL!"
    echo "File: classicsviewer_sample.zim"
    echo "Size: $SIZE"
    echo ""
    echo "Test with:"
    echo "  open -a Kiwix classicsviewer_sample.zim"
    echo "  or"
    echo "  kiwix-serve --port 8080 classicsviewer_sample.zim"
    echo "============================================"
else
    echo "❌ ERROR: ZIM file not created"
    exit 1
fi