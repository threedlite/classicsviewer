#!/bin/bash
set -e  # Exit on any error

echo "======================================================================="
echo "Sanskrit Pipeline - Complete Rebuild"
echo "======================================================================="

# Step 1: Build Sanskrit database
echo ""
echo "Step 1/5: Building Sanskrit database (270 works)..."
python3 create_sanskrit_database_interlinear.py full
if [ ! -f "sanskrit_texts.db" ]; then
    echo "ERROR: sanskrit_texts.db not created"
    exit 1
fi
echo "✓ Database created: $(ls -lh sanskrit_texts.db | awk '{print $5}')"

# Verify work count
WORK_COUNT=$(sqlite3 sanskrit_texts.db "SELECT COUNT(*) FROM works")
if [ "$WORK_COUNT" != "270" ]; then
    echo "ERROR: Expected 270 works, found $WORK_COUNT"
    exit 1
fi
echo "✓ Verified: 270 works in database"

# Step 2: Generate interlinear XML files
echo ""
echo "Step 2/5: Generating interlinear XML files (540 files)..."
mkdir -p interlinear_output
python3 batch_generate_interlinear.py sanskrit_texts.db \
    --output interlinear_output \
    --parallel 8

# Verify file count
XML_COUNT=$(find interlinear_output -name "*.dcs-eng99.xml" | wc -l | tr -d ' ')
if [ "$XML_COUNT" != "270" ]; then
    echo "ERROR: Expected 270 XML files, found $XML_COUNT"
    exit 1
fi
echo "✓ Verified: 270 interlinear XML files generated"

# Step 3: Verify book IDs match between database and XML
echo ""
echo "Step 3/5: Verifying database/XML consistency..."
python3 verify_interlinear_ready.py interlinear_output
if [ $? -ne 0 ]; then
    echo "ERROR: Verification failed - book IDs don't match"
    exit 1
fi
echo "✓ Verified: All book IDs match between database and XML"

# Step 4: Add interlinear to Sanskrit database
echo ""
echo "Step 4/5: Importing Sanskrit interlinear into database..."
# Import Sanskrit interlinear directly into sanskrit_texts.db
python3 import_sanskrit_interlinear.py sanskrit_texts.db interlinear_output

# Verify Sanskrit interlinear
SANSKRIT_WORKS=$(sqlite3 sanskrit_texts.db "SELECT COUNT(*) FROM works")
if [ "$SANSKRIT_WORKS" != "270" ]; then
    echo "ERROR: Expected 270 Sanskrit works, found $SANSKRIT_WORKS"
    exit 1
fi
echo "✓ Verified: 270 Sanskrit works in database"

# Verify interlinear import
INTERLINEAR_BOOKS=$(sqlite3 sanskrit_texts.db \
    "SELECT COUNT(DISTINCT book_id) FROM translation_segments WHERE translator LIKE 'Interlinear%'")
echo "✓ Verified: $INTERLINEAR_BOOKS Sanskrit books have interlinear translations"

if [ "$INTERLINEAR_BOOKS" -lt 2000 ]; then
    echo "⚠️  Warning: Expected ~2136 books with interlinear, found $INTERLINEAR_BOOKS"
fi

# Step 5: Compress final database (after all modifications)
echo ""
echo "Step 5/5: Compressing final database..."
rm -f sanskrit_texts.db.zip
zip -9 sanskrit_texts.db.zip sanskrit_texts.db
if [ ! -f "sanskrit_texts.db.zip" ]; then
    echo "ERROR: Failed to create sanskrit_texts.db.zip"
    exit 1
fi
ZIP_SIZE=$(ls -lh sanskrit_texts.db.zip | awk '{print $5}')
echo "✓ Created: sanskrit_texts.db.zip ($ZIP_SIZE)"

echo ""
echo "======================================================================="
echo "✅ Sanskrit Pipeline Complete"
echo "======================================================================="
echo "Output: sanskrit_texts.db ($ZIP_SIZE compressed)"
echo "Sanskrit works: $SANSKRIT_WORKS"
echo "Books with interlinear: $INTERLINEAR_BOOKS"
echo ""
echo "This database will be merged into extended database using merge_database.py"
