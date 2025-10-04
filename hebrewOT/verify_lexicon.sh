#!/bin/bash
# Verify hebrew_lexicon.zip integrity and format

echo "Hebrew Lexicon Verification"
echo "============================"
echo ""

# Check file exists
if [ ! -f "hebrew_lexicon.zip" ]; then
    echo "ERROR: hebrew_lexicon.zip not found!"
    exit 1
fi

# Check ZIP integrity
echo "1. Testing ZIP integrity..."
unzip -t hebrew_lexicon.zip > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ ZIP file is valid"
else
    echo "   ✗ ZIP file is corrupted!"
    exit 1
fi

# Check contents
echo ""
echo "2. Checking ZIP contents..."
unzip -l hebrew_lexicon.zip | grep -E '(dictionary|morphology|normalization_rules)\.csv'
if [ $? -eq 0 ]; then
    echo "   ✓ Contains required CSV files"
else
    echo "   ✗ Missing required CSV files!"
    exit 1
fi

# Check file sizes
echo ""
echo "3. File statistics..."
ZIP_SIZE=$(ls -lh hebrew_lexicon.zip | awk '{print $5}')
echo "   ZIP size: $ZIP_SIZE"

DICT_LINES=$(wc -l < hebrew_dictionary.csv)
MORPH_LINES=$(wc -l < hebrew_morphology.csv)
echo "   Dictionary entries: $((DICT_LINES - 1))"
echo "   Morphology mappings: $((MORPH_LINES - 1))"

echo ""
echo "4. Sample dictionary entries..."
head -5 hebrew_dictionary.csv | tail -4 | cut -d',' -f1,3 | while IFS=',' read lemma def; do
    echo "   $lemma: ${def:0:50}..."
done

echo ""
echo "5. Sample morphology mappings..."
head -5 hebrew_morphology.csv | tail -4 | cut -d',' -f1-3 | while IFS=',' read word lemma morph; do
    echo "   $word → $lemma ($morph)"
done

echo ""
echo "6. Normalization rules..."
if [ -f "normalization_rules_hebrew.csv" ]; then
    NORM_RULES=$(wc -l < normalization_rules_hebrew.csv)
    echo "   ✓ $((NORM_RULES - 1)) normalization rules included"
    echo "   Rules: Remove nikud, normalize final forms"
else
    echo "   ⚠ No normalization rules found"
fi

echo ""
echo "============================"
echo "Verification complete!"
echo "Ready for import into ClassicsViewer app"
