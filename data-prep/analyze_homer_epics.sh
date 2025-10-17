#!/bin/bash

DB="perseus_texts_full.db"
OUTPUT_DIR="homer_epics_coverage"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "HOMER EPIC POEMS DICTIONARY COVERAGE"
echo "=========================================="
echo ""

# Analyze Iliad
echo "Analyzing Iliad (24 books)..."
python3 check_dictionary_coverage.py \
    --db "$DB" \
    --work-id tlg0012.tlg001 \
    --csv "${OUTPUT_DIR}/iliad_complete_coverage.csv" \
    > "${OUTPUT_DIR}/iliad_analysis.log" 2>&1

if [ -f "${OUTPUT_DIR}/iliad_complete_coverage.csv" ]; then
    iliad_total=$(tail -n +2 "${OUTPUT_DIR}/iliad_complete_coverage.csv" | wc -l | tr -d ' ')
    iliad_has_def=$(grep ",has_definition," "${OUTPUT_DIR}/iliad_complete_coverage.csv" | wc -l | tr -d ' ')
    iliad_morph=$(grep ",morphology_only," "${OUTPUT_DIR}/iliad_complete_coverage.csv" | wc -l | tr -d ' ')
    iliad_none=$(grep ",no_entry," "${OUTPUT_DIR}/iliad_complete_coverage.csv" | wc -l | tr -d ' ')
    
    echo "  Total unique words: $iliad_total"
    echo "  With definitions: $iliad_has_def ($(echo "scale=1; $iliad_has_def * 100 / $iliad_total" | bc)%)"
    echo "  Morphology only: $iliad_morph ($(echo "scale=1; $iliad_morph * 100 / $iliad_total" | bc)%)"
    echo "  NO entry: $iliad_none ($(echo "scale=1; $iliad_none * 100 / $iliad_total" | bc)%)"
    echo ""
fi

# Analyze Odyssey
echo "Analyzing Odyssey (24 books)..."
python3 check_dictionary_coverage.py \
    --db "$DB" \
    --work-id tlg0012.tlg002 \
    --csv "${OUTPUT_DIR}/odyssey_complete_coverage.csv" \
    > "${OUTPUT_DIR}/odyssey_analysis.log" 2>&1

if [ -f "${OUTPUT_DIR}/odyssey_complete_coverage.csv" ]; then
    odyssey_total=$(tail -n +2 "${OUTPUT_DIR}/odyssey_complete_coverage.csv" | wc -l | tr -d ' ')
    odyssey_has_def=$(grep ",has_definition," "${OUTPUT_DIR}/odyssey_complete_coverage.csv" | wc -l | tr -d ' ')
    odyssey_morph=$(grep ",morphology_only," "${OUTPUT_DIR}/odyssey_complete_coverage.csv" | wc -l | tr -d ' ')
    odyssey_none=$(grep ",no_entry," "${OUTPUT_DIR}/odyssey_complete_coverage.csv" | wc -l | tr -d ' ')
    
    echo "  Total unique words: $odyssey_total"
    echo "  With definitions: $odyssey_has_def ($(echo "scale=1; $odyssey_has_def * 100 / $odyssey_total" | bc)%)"
    echo "  Morphology only: $odyssey_morph ($(echo "scale=1; $odyssey_morph * 100 / $odyssey_total" | bc)%)"
    echo "  NO entry: $odyssey_none ($(echo "scale=1; $odyssey_none * 100 / $odyssey_total" | bc)%)"
    echo ""
fi

# Combined analysis
echo "=========================================="
echo "COMBINED STATISTICS"
echo "=========================================="

# Merge both CSV files (avoiding header duplication)
cat "${OUTPUT_DIR}/iliad_complete_coverage.csv" > "${OUTPUT_DIR}/homer_combined_coverage.csv"
tail -n +2 "${OUTPUT_DIR}/odyssey_complete_coverage.csv" >> "${OUTPUT_DIR}/homer_combined_coverage.csv"

combined_total=$(tail -n +2 "${OUTPUT_DIR}/homer_combined_coverage.csv" | wc -l | tr -d ' ')
combined_has_def=$(grep ",has_definition," "${OUTPUT_DIR}/homer_combined_coverage.csv" | wc -l | tr -d ' ')
combined_morph=$(grep ",morphology_only," "${OUTPUT_DIR}/homer_combined_coverage.csv" | wc -l | tr -d ' ')
combined_none=$(grep ",no_entry," "${OUTPUT_DIR}/homer_combined_coverage.csv" | wc -l | tr -d ' ')

# Get unique words across both works
combined_unique=$(tail -n +2 "${OUTPUT_DIR}/homer_combined_coverage.csv" | cut -d',' -f1 | sort -u | wc -l | tr -d ' ')

echo "Total words (with duplicates): $combined_total"
echo "Total UNIQUE words: $combined_unique"
echo "With definitions: $combined_has_def ($(echo "scale=1; $combined_has_def * 100 / $combined_total" | bc)%)"
echo "Morphology only: $combined_morph ($(echo "scale=1; $combined_morph * 100 / $combined_total" | bc)%)"
echo "NO entry: $combined_none ($(echo "scale=1; $combined_none * 100 / $combined_total" | bc)%)"
echo ""

echo "=========================================="
echo "WORDS WITH NO DICTIONARY ENTRY"
echo "=========================================="
echo ""

# Show missing words from both works
echo "=== ILIAD - Words with NO entry ==="
grep ",no_entry," "${OUTPUT_DIR}/iliad_complete_coverage.csv" | cut -d',' -f1 | head -30
if [ $iliad_none -gt 30 ]; then
    echo "... and $((iliad_none - 30)) more"
fi
echo ""

echo "=== ODYSSEY - Words with NO entry ==="
grep ",no_entry," "${OUTPUT_DIR}/odyssey_complete_coverage.csv" | cut -d',' -f1 | head -30
if [ $odyssey_none -gt 30 ]; then
    echo "... and $((odyssey_none - 30)) more"
fi
echo ""

echo "=========================================="
echo "OUTPUT FILES"
echo "=========================================="
echo "  Iliad CSV: ${OUTPUT_DIR}/iliad_complete_coverage.csv"
echo "  Odyssey CSV: ${OUTPUT_DIR}/odyssey_complete_coverage.csv"
echo "  Combined CSV: ${OUTPUT_DIR}/homer_combined_coverage.csv"
echo "  Full logs: ${OUTPUT_DIR}/*.log"
echo ""
echo "Complete!"
