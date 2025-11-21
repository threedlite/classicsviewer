#!/bin/bash
# Build language-specific ZIM files from extended database
# This creates separate, smaller ZIM files for each language

set -e  # Exit on error

# Check if language parameter provided
if [ $# -eq 0 ]; then
    echo "Usage: ./build_by_language.sh <language>"
    echo ""
    echo "Available languages:"
    echo "  greek     - Greek texts only (Perseus + First1K)"
    echo "  latin     - Latin texts only (Perseus)"
    echo "  sanskrit  - Sanskrit texts only"
    echo "  arabic    - Arabic texts only"
    echo "  hebrew    - Hebrew texts only"
    echo "  persian   - Persian texts only"
    echo "  akkadian  - Akkadian texts only"
    echo "  sumerian  - Sumerian texts only"
    echo "  all       - Build all language ZIMs"
    echo ""
    exit 1
fi

LANGUAGE=$1

# Function to build a single language ZIM
build_language_zim() {
    local lang=$1
    local lang_upper=$(echo "$lang" | tr '[:lower:]' '[:upper:]')

    echo "============================================"
    echo "    ${lang_upper} ZIM BUILD"
    echo "    From Extended Database"
    echo "============================================"
    echo ""

    # Step 1: Clean environment
    echo "[1/5] Cleaning environment..."
    killall python3 2>/dev/null || true
    killall Python 2>/dev/null || true
    rm -f /tmp/*.lock
    # Rename old folder instead of deleting (much faster)
    if [ -d "zim_content_optimized" ]; then
        mv zim_content_optimized "zim_content_optimized_old_$(date +%s)" 2>/dev/null || true
    fi
    echo "✓ Environment cleaned"
    echo ""

    # Step 2: Activate virtual environment
    echo "[2/5] Activating Python environment..."
    source venv/bin/activate
    echo "✓ Virtual environment activated"
    echo ""

    # Step 3: Generate content
    echo "[3/5] Generating HTML content for ${lang}..."
    python3 create_zim_content_optimized.py --extended --language ${lang}
    echo "✓ Content generation complete"
    echo ""

    # Step 4: Count generated files
    FILE_COUNT=$(find zim_content_optimized -name "*.html" 2>/dev/null | wc -l | tr -d ' ')
    echo "[4/5] Generated $FILE_COUNT HTML files"
    echo ""

    # Step 5: Create ZIM file
    echo "[5/5] Creating ZIM archive..."
    python3 create_zim_optimized.py --output classicsviewer_${lang}.zim
    echo ""

    # Final verification
    if [ -f "classicsviewer_${lang}.zim" ]; then
        SIZE=$(ls -lh classicsviewer_${lang}.zim | awk '{print $5}')
        echo "============================================"
        echo "✓ BUILD SUCCESSFUL!"
        echo "File: classicsviewer_${lang}.zim"
        echo "Size: $SIZE"
        echo ""
        echo "Test with:"
        echo "  open -a Kiwix classicsviewer_${lang}.zim"
        echo "  or"
        echo "  kiwix-serve --port 8080 classicsviewer_${lang}.zim"
        echo "============================================"
    else
        echo "❌ ERROR: ZIM file not created"
        return 1
    fi
}

# Build requested language(s)
if [ "$LANGUAGE" = "all" ]; then
    echo "Building all language ZIMs..."
    for lang in greek latin sanskrit arabic hebrew persian akkadian sumerian; do
        build_language_zim $lang
        echo ""
        echo ""
    done
else
    build_language_zim $LANGUAGE
fi
